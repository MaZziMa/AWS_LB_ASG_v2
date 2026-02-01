import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError, NoCredentialsError, PartialCredentialsError


_DISCOVERY_TTL_SECONDS = int(os.getenv("OPS_DISCOVERY_TTL_SECONDS", "30"))
_SNAPSHOT_TTL_SECONDS = float(os.getenv("OPS_SNAPSHOT_TTL_SECONDS", "3"))
_SNAPSHOT_LOG_STREAM = os.getenv("OPS_SNAPSHOT_LOG_STREAM", "ops-snapshots")
_SNAPSHOT_LOG_GROUP = os.getenv("OPS_SNAPSHOT_LOG_GROUP") or os.getenv("CLOUDWATCH_LOG_GROUP") or os.getenv("CW_LOG_GROUP")
_discovery_cache: Dict[str, Any] = {"expires_at": 0.0, "region": None, "values": None, "errors": None}
_snapshot_cache: Dict[str, Any] = {"expires_at": 0.0, "key": None, "value": None}


def _now_utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_boto_error(e: Exception) -> Dict[str, Any]:
    if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
        return {"type": type(e).__name__, "message": "AWS credentials not available"}
    if isinstance(e, EndpointConnectionError):
        return {"type": type(e).__name__, "message": f"AWS endpoint connection error: {e}"}
    if isinstance(e, ClientError):
        err = e.response.get("Error", {})
        return {"type": err.get("Code", "ClientError"), "message": err.get("Message", str(e))}
    if isinstance(e, BotoCoreError):
        return {"type": type(e).__name__, "message": str(e)}
    return {"type": type(e).__name__, "message": str(e)}


def _logs_client(region: str):
    return boto3.client("logs", region_name=region)


def _put_log_event(
    *,
    region: str,
    log_group: str,
    log_stream: str,
    message: str,
) -> Dict[str, Any]:
    """Best-effort PutLogEvents with sequence token handling."""

    client = _logs_client(region)

    try:
        seq_token = None
        try:
            desc = client.describe_log_streams(logGroupName=log_group, logStreamNamePrefix=log_stream, limit=1)
            streams = desc.get("logStreams", []) or []
            if streams:
                seq_token = streams[0].get("uploadSequenceToken")
            else:
                client.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
        except client.exceptions.ResourceNotFoundException:
            client.create_log_group(logGroupName=log_group)
            client.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
        except Exception as e:  # pragma: no cover - defensive
            return {"ok": False, "error": _safe_boto_error(e)}

        kwargs = {
            "logGroupName": log_group,
            "logStreamName": log_stream,
            "logEvents": [
                {
                    "timestamp": int(time.time() * 1000),
                    "message": message,
                }
            ],
        }
        if seq_token:
            kwargs["sequenceToken"] = seq_token

        resp = client.put_log_events(**kwargs)
        return {"ok": True, "next_sequence_token": resp.get("nextSequenceToken")}
    except client.exceptions.InvalidSequenceTokenException as e:
        return {"ok": False, "retry": True, "error": _safe_boto_error(e)}
    except Exception as e:  # pragma: no cover - defensive
        return {"ok": False, "error": _safe_boto_error(e)}


def _imds_v2_token(timeout_seconds: float = 0.5) -> Optional[str]:
    """Fetch an IMDSv2 token. Returns None if IMDS is unavailable."""

    try:
        req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def _imds_get(path: str, timeout_seconds: float = 0.5) -> Optional[str]:
    token = _imds_v2_token(timeout_seconds=timeout_seconds)
    headers = {"X-aws-ec2-metadata-token": token} if token else {}

    try:
        req = urllib.request.Request(f"http://169.254.169.254/latest/{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:
        return None


def _instance_id_from_imds() -> Optional[str]:
    return _imds_get("meta-data/instance-id")


def _discover_by_tags(
    *,
    region: str,
    project_tag_value: Optional[str],
    environment_tag_value: Optional[str],
) -> Dict[str, Optional[str]]:
    """Best-effort discovery using AWS Resource Groups Tagging API."""

    if not (project_tag_value or environment_tag_value):
        return {"asg_name": None, "target_group_arn": None, "alb_arn": None}

    tag_filters = []
    if project_tag_value:
        tag_filters.append({"Key": "Project", "Values": [project_tag_value]})
    if environment_tag_value:
        tag_filters.append({"Key": "Environment", "Values": [environment_tag_value]})

    client = boto3.client("resourcegroupstaggingapi", region_name=region)

    def first_arn(resource_type: str) -> Optional[str]:
        paginator = client.get_paginator("get_resources")
        for page in paginator.paginate(ResourceTypeFilters=[resource_type], TagFilters=tag_filters):
            mappings = page.get("ResourceTagMappingList", []) or []
            if mappings:
                return mappings[0].get("ResourceARN")
        return None

    asg_arn = first_arn("autoscaling:autoScalingGroup")
    tg_arn = first_arn("elasticloadbalancing:targetgroup")
    alb_arn = first_arn("elasticloadbalancing:loadbalancer")

    asg_name = None
    if asg_arn and "/" in asg_arn:
        asg_name = asg_arn.split("/")[-1]

    return {"asg_name": asg_name, "target_group_arn": tg_arn, "alb_arn": alb_arn}


def resolve_infra_identifiers(
    *,
    region: str,
    asg_name: Optional[str],
    target_group_arn: Optional[str],
    alb_arn: Optional[str],
) -> Dict[str, Any]:
    """Resolve missing infra identifiers."""

    if asg_name and target_group_arn and alb_arn:
        return {
            "asg_name": asg_name,
            "target_group_arn": target_group_arn,
            "alb_arn": alb_arn,
            "discovery": {"method": "explicit", "errors": {}},
        }

    now = time.time()
    if (
        _discovery_cache.get("values")
        and _discovery_cache.get("region") == region
        and float(_discovery_cache.get("expires_at", 0.0)) > now
    ):
        cached = _discovery_cache["values"]
        return {
            "asg_name": asg_name or cached.get("asg_name"),
            "target_group_arn": target_group_arn or cached.get("target_group_arn"),
            "alb_arn": alb_arn or cached.get("alb_arn"),
            "discovery": {"method": "cache", "errors": _discovery_cache.get("errors") or {}},
        }

    errors: Dict[str, Any] = {}
    resolved_asg = asg_name or default_asg_name()
    resolved_tg = target_group_arn or default_target_group_arn()
    resolved_alb = alb_arn or default_alb_arn()

    if not (resolved_asg and resolved_tg and resolved_alb):
        project_tag_val = os.getenv("OPS_DISCOVERY_PROJECT_TAG") or os.getenv("PROJECT_TAG")
        env_tag_val = os.getenv("OPS_DISCOVERY_ENVIRONMENT_TAG") or os.getenv("ENVIRONMENT")
        try:
            by_tags = _discover_by_tags(
                region=region,
                project_tag_value=project_tag_val,
                environment_tag_value=env_tag_val,
            )
            resolved_asg = resolved_asg or by_tags.get("asg_name")
            resolved_tg = resolved_tg or by_tags.get("target_group_arn")
            resolved_alb = resolved_alb or by_tags.get("alb_arn")
            if any(by_tags.values()):
                errors["tag_discovery"] = {"type": "Info", "message": "Resolved some identifiers via tags"}
        except Exception as e:
            errors["tag_discovery"] = _safe_boto_error(e)

    autoscaling = boto3.client("autoscaling", region_name=region)
    elbv2 = boto3.client("elbv2", region_name=region)

    if not resolved_asg:
        instance_id = _instance_id_from_imds()
        if instance_id:
            try:
                asi = autoscaling.describe_auto_scaling_instances(InstanceIds=[instance_id])
                instances = asi.get("AutoScalingInstances", []) or []
                if instances:
                    resolved_asg = instances[0].get("AutoScalingGroupName")
            except Exception as e:
                errors["instance_discovery"] = _safe_boto_error(e)
        else:
            errors["instance_discovery"] = {"type": "Unavailable", "message": "Not running on EC2 or IMDS blocked"}

    if resolved_asg and not resolved_tg:
        try:
            resp = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[resolved_asg])
            groups = resp.get("AutoScalingGroups", []) or []
            if groups:
                tgs = groups[0].get("TargetGroupARNs", []) or []
                if tgs:
                    resolved_tg = tgs[0]
        except Exception as e:
            errors["asg_target_groups"] = _safe_boto_error(e)

    if resolved_tg and not resolved_alb:
        try:
            tg_resp = elbv2.describe_target_groups(TargetGroupArns=[resolved_tg])
            tgs = tg_resp.get("TargetGroups", []) or []
            if tgs:
                lbs = tgs[0].get("LoadBalancerArns", []) or []
                if lbs:
                    resolved_alb = lbs[0]
        except Exception as e:
            errors["target_group_lbs"] = _safe_boto_error(e)

    values = {"asg_name": resolved_asg, "target_group_arn": resolved_tg, "alb_arn": resolved_alb}
    _discovery_cache.update(
        {
            "expires_at": now + max(1, _DISCOVERY_TTL_SECONDS),
            "region": region,
            "values": values,
            "errors": errors,
        }
    )

    return {**values, "discovery": {"method": "resolved", "errors": errors}}


def summarize_target_health(target_descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    by_target: List[Dict[str, Any]] = []

    for td in target_descriptions:
        target = td.get("Target", {}) or {}
        health = td.get("TargetHealth", {}) or {}
        state = health.get("State") or "unknown"
        counts[state] = counts.get(state, 0) + 1
        by_target.append(
            {
                "target": target,
                "state": state,
                "reason": health.get("Reason"),
                "description": health.get("Description"),
            }
        )

    return {"counts": counts, "targets": by_target}


def summarize_asg(asg: Dict[str, Any]) -> Dict[str, Any]:
    instances = asg.get("Instances", []) or []
    instance_counts: Dict[str, int] = {}
    health_counts: Dict[str, int] = {}
    lifecycle_counts: Dict[str, int] = {}

    for inst in instances:
        health = inst.get("HealthStatus") or "unknown"
        lifecycle = inst.get("LifecycleState") or "unknown"
        health_counts[health] = health_counts.get(health, 0) + 1
        lifecycle_counts[lifecycle] = lifecycle_counts.get(lifecycle, 0) + 1

        state = f"{health}/{lifecycle}"
        instance_counts[state] = instance_counts.get(state, 0) + 1

    return {
        "auto_scaling_group_name": asg.get("AutoScalingGroupName"),
        "min_size": asg.get("MinSize"),
        "max_size": asg.get("MaxSize"),
        "desired_capacity": asg.get("DesiredCapacity"),
        "instance_count": len(instances),
        "health_counts": health_counts,
        "lifecycle_counts": lifecycle_counts,
        "instances": [
            {
                "instance_id": i.get("InstanceId"),
                "availability_zone": i.get("AvailabilityZone"),
                "health_status": i.get("HealthStatus"),
                "lifecycle_state": i.get("LifecycleState"),
                "launch_template": i.get("LaunchTemplate"),
            }
            for i in instances
        ],
    }


def collect_infra_snapshot(
    *,
    region: str,
    asg_name: Optional[str] = None,
    target_group_arn: Optional[str] = None,
    alb_arn: Optional[str] = None,
    include_activity_limit: int = 10,
) -> Dict[str, Any]:
    """Collect a best-effort snapshot of ALB/TG/ASG state."""

    snapshot: Dict[str, Any] = {
        "timestamp": _now_utc_iso(),
        "region": region,
        "inputs": {
            "asg_name": asg_name,
            "target_group_arn": target_group_arn,
            "alb_arn": alb_arn,
        },
        "asg": None,
        "instance_refresh": None,
        "scaling_activities": [],
        "target_group": None,
        "alb": None,
        "errors": {},
    }

    autoscaling = boto3.client("autoscaling", region_name=region)
    elbv2 = boto3.client("elbv2", region_name=region)

    if asg_name:
        try:
            resp = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
            groups = resp.get("AutoScalingGroups", []) or []
            if groups:
                snapshot["asg"] = summarize_asg(groups[0])
            else:
                snapshot["errors"]["asg"] = {"type": "NotFound", "message": f"ASG not found: {asg_name}"}
        except Exception as e:
            snapshot["errors"]["asg"] = _safe_boto_error(e)

        try:
            rr = autoscaling.describe_instance_refreshes(
                AutoScalingGroupName=asg_name,
                MaxRecords=1,
            )
            refreshes = rr.get("InstanceRefreshes", []) or []
            if refreshes:
                r0 = refreshes[0]
                snapshot["instance_refresh"] = {
                    "instance_refresh_id": r0.get("InstanceRefreshId"),
                    "status": r0.get("Status"),
                    "status_reason": r0.get("StatusReason"),
                    "start_time": str(r0.get("StartTime")) if r0.get("StartTime") else None,
                    "end_time": str(r0.get("EndTime")) if r0.get("EndTime") else None,
                    "percentage_complete": r0.get("PercentageComplete"),
                }
        except Exception as e:
            snapshot["errors"]["instance_refresh"] = _safe_boto_error(e)

        try:
            act = autoscaling.describe_scaling_activities(
                AutoScalingGroupName=asg_name,
                MaxRecords=max(1, min(include_activity_limit, 50)),
            )
            activities = act.get("Activities", []) or []
            snapshot["scaling_activities"] = [
                {
                    "activity_id": a.get("ActivityId"),
                    "status_code": a.get("StatusCode"),
                    "description": a.get("Description"),
                    "cause": a.get("Cause"),
                    "start_time": str(a.get("StartTime")) if a.get("StartTime") else None,
                    "end_time": str(a.get("EndTime")) if a.get("EndTime") else None,
                    "progress": a.get("Progress"),
                }
                for a in activities
            ]
        except Exception as e:
            snapshot["errors"]["scaling_activities"] = _safe_boto_error(e)

    if target_group_arn:
        try:
            th = elbv2.describe_target_health(TargetGroupArn=target_group_arn)
            tds = th.get("TargetHealthDescriptions", []) or []
            summary = summarize_target_health(tds)
            snapshot["target_group"] = {
                "target_group_arn": target_group_arn,
                "counts": summary["counts"],
                "targets": summary["targets"],
            }
        except Exception as e:
            snapshot["errors"]["target_group"] = _safe_boto_error(e)

    if alb_arn:
        try:
            lbs = elbv2.describe_load_balancers(LoadBalancerArns=[alb_arn]).get("LoadBalancers", []) or []
            if lbs:
                lb = lbs[0]
                snapshot["alb"] = {
                    "load_balancer_arn": alb_arn,
                    "dns_name": lb.get("DNSName"),
                    "state": (lb.get("State") or {}).get("Code"),
                    "type": lb.get("Type"),
                    "scheme": lb.get("Scheme"),
                    "vpc_id": lb.get("VpcId"),
                    "availability_zones": [
                        {
                            "zone": az.get("ZoneName"),
                            "subnet_id": az.get("SubnetId"),
                        }
                        for az in (lb.get("AvailabilityZones", []) or [])
                    ],
                }
            else:
                snapshot["errors"]["alb"] = {"type": "NotFound", "message": f"ALB not found: {alb_arn}"}
        except Exception as e:
            snapshot["errors"]["alb"] = _safe_boto_error(e)

    return snapshot


def collect_infra_snapshot_cached(
    *,
    region: str,
    asg_name: Optional[str] = None,
    target_group_arn: Optional[str] = None,
    alb_arn: Optional[str] = None,
    include_activity_limit: int = 10,
    ttl_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """Small TTL cache around collect_infra_snapshot."""

    ttl = _SNAPSHOT_TTL_SECONDS if ttl_seconds is None else float(ttl_seconds)
    ttl = max(0.0, min(ttl, 30.0))

    key = (
        region,
        asg_name or "",
        target_group_arn or "",
        alb_arn or "",
        int(include_activity_limit),
    )

    now = time.time()
    if ttl > 0 and _snapshot_cache.get("key") == key and float(_snapshot_cache.get("expires_at", 0.0)) > now:
        cached = _snapshot_cache.get("value")
        if isinstance(cached, dict):
            out = dict(cached)
            out["cache"] = {"hit": True, "ttl_seconds": ttl}
            return out

    snap = collect_infra_snapshot(
        region=region,
        asg_name=asg_name,
        target_group_arn=target_group_arn,
        alb_arn=alb_arn,
        include_activity_limit=include_activity_limit,
    )
    snap["cache"] = {"hit": False, "ttl_seconds": ttl}

    if ttl > 0:
        _snapshot_cache.update({"key": key, "value": snap, "expires_at": now + ttl})

    return snap


def persist_snapshot_to_logs(
    *,
    region: str,
    snapshot: Dict[str, Any],
    log_group: Optional[str] = None,
    log_stream: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a snapshot JSON line into CloudWatch Logs."""

    lg = log_group or _SNAPSHOT_LOG_GROUP
    ls = log_stream or _SNAPSHOT_LOG_STREAM
    if not lg or not ls:
        return {"ok": False, "error": {"type": "MissingConfig", "message": "log group/stream not configured"}}

    message = json.dumps({"log_type": "ops_snapshot", **snapshot}, ensure_ascii=False, separators=(",", ":"))
    return _put_log_event(region=region, log_group=lg, log_stream=ls, message=message)


def default_region() -> str:
    return os.getenv("AWS_REGION", "us-east-1")


def default_asg_name() -> Optional[str]:
    return os.getenv("OPS_ASG_NAME") or os.getenv("ASG_NAME")


def default_target_group_arn() -> Optional[str]:
    return os.getenv("OPS_TARGET_GROUP_ARN") or os.getenv("TARGET_GROUP_ARN")


def default_alb_arn() -> Optional[str]:
    return os.getenv("OPS_ALB_ARN") or os.getenv("ALB_ARN")


def collect_dynamodb_metrics(
    *,
    region: str,
    table_names: Sequence[str],
    minutes: int = 5,
) -> Dict[str, Any]:
    """Lightweight DynamoDB metrics snapshot from CloudWatch."""

    cw = boto3.client("cloudwatch", region_name=region)
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=max(1, min(minutes, 60)))
    metrics = [
        "ConsumedReadCapacityUnits",
        "ConsumedWriteCapacityUnits",
        "ProvisionedReadCapacityUnits",
        "ProvisionedWriteCapacityUnits",
        "ReadThrottleEvents",
        "WriteThrottleEvents",
        "ThrottledRequests",
        "SuccessfulRequestLatency",
        "SystemErrors",
        "UserErrors",
    ]

    def latest_point(name: str, dim: Dict[str, str]) -> Optional[Dict[str, Any]]:
        try:
            res = cw.get_metric_statistics(
                Namespace="AWS/DynamoDB",
                MetricName=name,
                Dimensions=[dim],
                StartTime=start,
                EndTime=end,
                Period=60,
                Statistics=["Sum", "Average", "Maximum"],
            )
            dps = res.get("Datapoints", []) or []
            if not dps:
                return None
            latest = max(dps, key=lambda x: x.get("Timestamp", start))
            return {
                "sum": latest.get("Sum"),
                "average": latest.get("Average"),
                "maximum": latest.get("Maximum"),
                "unit": latest.get("Unit"),
                "timestamp": latest.get("Timestamp").isoformat() if latest.get("Timestamp") else None,
            }
        except Exception as e:  # best-effort
            return {"error": _safe_boto_error(e)}

    out: Dict[str, Any] = {"region": region, "window_minutes": minutes, "tables": {}}
    for name in table_names:
        name = name.strip()
        if not name:
            continue
        table_dim = {"Name": "TableName", "Value": name}
        table_data: Dict[str, Any] = {"metrics": {}}
        for m in metrics:
            table_data["metrics"][m] = latest_point(m, table_dim)
        try:
            ddb = boto3.client("dynamodb", region_name=region)
            desc = ddb.describe_table(TableName=name)
            gsis = desc.get("Table", {}).get("GlobalSecondaryIndexes", []) or []
            if gsis:
                gsi_entries: Dict[str, Any] = {}
                for g in gsis:
                    g_name = g.get("IndexName")
                    if not g_name:
                        continue
                    dim = {"Name": "GlobalSecondaryIndexName", "Value": g_name}
                    gsi_metrics = {
                        "ConsumedReadCapacityUnits": latest_point(
                            "ConsumedReadCapacityUnits", {"Name": "TableName", "Value": name}
                        ),
                        "ConsumedWriteCapacityUnits": latest_point(
                            "ConsumedWriteCapacityUnits", {"Name": "TableName", "Value": name}
                        ),
                        "ReadThrottleEvents": latest_point("ReadThrottleEvents", dim),
                        "WriteThrottleEvents": latest_point("WriteThrottleEvents", dim),
                        "ThrottledRequests": latest_point("ThrottledRequests", dim),
                    }
                    gsi_entries[g_name] = gsi_metrics
                table_data["gsi"] = gsi_entries
            billing = desc.get("Table", {}).get("BillingModeSummary", {}) or {}
            table_data["billing_mode"] = billing.get("BillingMode", "UNKNOWN")
            throughput = desc.get("Table", {}).get("ProvisionedThroughput", {}) or {}
            if throughput:
                table_data["provisioned_throughput"] = {
                    "read": throughput.get("ReadCapacityUnits"),
                    "write": throughput.get("WriteCapacityUnits"),
                }
        except Exception as e:  # pragma: no cover
            table_data["describe_error"] = _safe_boto_error(e)

        out["tables"][name] = table_data

    return out


async def sse_infra_stream(
    *,
    region: str,
    asg_name: Optional[str],
    target_group_arn: Optional[str],
    alb_arn: Optional[str],
    interval_seconds: int,
    max_events: int,
) -> AsyncIterator[str]:
    interval = max(1, min(interval_seconds, 30))
    remaining = max(1, min(max_events, 600))

    yield ": connected\n\n"

    while remaining > 0:
        remaining -= 1
        payload = collect_infra_snapshot_cached(
            region=region,
            asg_name=asg_name,
            target_group_arn=target_group_arn,
            alb_arn=alb_arn,
        )
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        yield f"event: infra\ndata: {data}\n\n"
        await asyncio.sleep(interval)


def plan_asg_instance_refresh(*, region: str, asg_name: str) -> Dict[str, Any]:
    """Prepare an ASG instance refresh action plan."""

    return {
        "action": "asg_instance_refresh",
        "asg_name": asg_name,
        "region": region,
        "plan": {
            "strategy": "Rolling",
            "preferences": {
                "MinHealthyPercentage": 90,
                "InstanceWarmup": 60,
            },
        },
    }


def execute_asg_instance_refresh(*, region: str, asg_name: str) -> Dict[str, Any]:
    autoscaling = boto3.client("autoscaling", region_name=region)
    plan = plan_asg_instance_refresh(region=region, asg_name=asg_name)
    try:
        resp = autoscaling.start_instance_refresh(
            AutoScalingGroupName=asg_name,
            Strategy="Rolling",
            Preferences={"MinHealthyPercentage": 90, "InstanceWarmup": 60},
        )
        plan["started"] = True
        plan["instance_refresh_id"] = resp.get("InstanceRefreshId")
        return plan
    except Exception as e:  # pragma: no cover - runtime AWS
        plan["started"] = False
        plan["error"] = _safe_boto_error(e)
        return plan


def plan_ddb_capacity_increase(
    *,
    region: str,
    table_name: str,
    factor: float = 1.5,
    max_increment: int = 100,
) -> Dict[str, Any]:
    """Plan a bounded RCU/WCU increase for provisioned tables."""

    ddb = boto3.client("dynamodb", region_name=region)
    plan: Dict[str, Any] = {
        "action": "ddb_capacity_increase",
        "table_name": table_name,
        "region": region,
        "factor": factor,
        "max_increment": max_increment,
    }
    try:
        desc = ddb.describe_table(TableName=table_name)
        table = desc.get("Table", {}) or {}
        billing = table.get("BillingModeSummary", {}) or {}
        if billing.get("BillingMode") == "PAY_PER_REQUEST":
            plan["allowed"] = False
            plan["reason"] = "Table is ON_DEMAND"
            return plan
        throughput = table.get("ProvisionedThroughput", {}) or {}
        rc = throughput.get("ReadCapacityUnits")
        wc = throughput.get("WriteCapacityUnits")
        if rc is None or wc is None:
            plan["allowed"] = False
            plan["reason"] = "Throughput unavailable"
            return plan
        new_rc = min(int(rc * factor), rc + max_increment)
        new_wc = min(int(wc * factor), wc + max_increment)
        plan.update(
            {
                "allowed": True,
                "current": {"read": rc, "write": wc},
                "proposed": {"read": new_rc, "write": new_wc},
            }
        )
        return plan
    except Exception as e:  # pragma: no cover - runtime AWS
        plan["allowed"] = False
        plan["error"] = _safe_boto_error(e)
        return plan


def execute_ddb_capacity_increase(
    *,
    region: str,
    table_name: str,
    factor: float = 1.5,
    max_increment: int = 100,
) -> Dict[str, Any]:
    plan = plan_ddb_capacity_increase(region=region, table_name=table_name, factor=factor, max_increment=max_increment)
    if not plan.get("allowed"):
        return plan
    ddb = boto3.client("dynamodb", region_name=region)
    try:
        ddb.update_table(
            TableName=table_name,
            ProvisionedThroughput={
                "ReadCapacityUnits": plan["proposed"]["read"],
                "WriteCapacityUnits": plan["proposed"]["write"],
            },
        )
        plan["executed"] = True
        return plan
    except Exception as e:  # pragma: no cover - runtime AWS
        plan["executed"] = False
        plan["error"] = _safe_boto_error(e)
        return plan


# ==============================================================================
# API Health Check Functions
# ==============================================================================

def check_api_health(
    base_url: str,
    endpoints: Optional[List[str]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """Check health of API endpoints.
    
    Args:
        base_url: Base URL of the API (e.g., http://localhost:8000 or ALB DNS)
        endpoints: List of endpoints to check (default: ["/health", "/api/courses"])
        timeout: Request timeout in seconds
        
    Returns:
        dict with endpoint health status and response times
    """
    if endpoints is None:
        endpoints = ["/health", "/api/courses", "/api/students", "/api/enrollments"]
    
    results = {
        "timestamp": _now_utc_iso(),
        "base_url": base_url,
        "endpoints": {},
        "summary": {"healthy": 0, "unhealthy": 0, "total": len(endpoints)},
    }
    
    for endpoint in endpoints:
        url = f"{base_url.rstrip('/')}{endpoint}"
        endpoint_result = {
            "url": url,
            "healthy": False,
            "status_code": None,
            "response_time_ms": None,
            "error": None,
            "has_pagination": None,
            "sample_response": None,
        }
        
        try:
            start_time = time.time()
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                elapsed_ms = (time.time() - start_time) * 1000
                endpoint_result["status_code"] = response.status
                endpoint_result["response_time_ms"] = round(elapsed_ms, 2)
                endpoint_result["healthy"] = 200 <= response.status < 300
                
                # Try to parse JSON response
                try:
                    body = response.read().decode("utf-8")
                    data = json.loads(body)
                    
                    # Check for pagination indicators
                    pagination_keys = {"page", "limit", "offset", "total", "next", "previous", "items", "data", "results"}
                    if isinstance(data, dict):
                        found_keys = set(data.keys()) & pagination_keys
                        endpoint_result["has_pagination"] = len(found_keys) >= 2
                        endpoint_result["pagination_keys"] = list(found_keys) if found_keys else None
                        
                        # Sample response (truncated)
                        sample = {k: v for k, v in list(data.items())[:5]}
                        if isinstance(sample.get("items") or sample.get("data") or sample.get("results"), list):
                            key = next((k for k in ["items", "data", "results"] if k in sample), None)
                            if key and len(sample[key]) > 2:
                                sample[key] = sample[key][:2] + ["...truncated..."]
                        endpoint_result["sample_response"] = sample
                    elif isinstance(data, list):
                        endpoint_result["has_pagination"] = False
                        endpoint_result["sample_response"] = {"type": "array", "count": len(data)}
                        
                except json.JSONDecodeError:
                    endpoint_result["sample_response"] = {"type": "non-json"}
                    
        except urllib.error.HTTPError as e:
            endpoint_result["status_code"] = e.code
            endpoint_result["error"] = str(e.reason)
        except urllib.error.URLError as e:
            endpoint_result["error"] = f"Connection failed: {e.reason}"
        except Exception as e:
            endpoint_result["error"] = str(e)
        
        # Update summary
        if endpoint_result["healthy"]:
            results["summary"]["healthy"] += 1
        else:
            results["summary"]["unhealthy"] += 1
            
        results["endpoints"][endpoint] = endpoint_result
    
    return results


def check_api_pagination(
    base_url: str,
    endpoint: str = "/api/courses",
    timeout: int = 10,
) -> Dict[str, Any]:
    """Check if an API endpoint supports pagination.
    
    Tests with different pagination parameters to detect support.
    """
    result = {
        "timestamp": _now_utc_iso(),
        "endpoint": endpoint,
        "base_url": base_url,
        "supports_pagination": False,
        "pagination_style": None,
        "tests": [],
    }
    
    # Test different pagination styles
    pagination_tests = [
        {"params": "?page=1&limit=5", "style": "page/limit"},
        {"params": "?page=1&size=5", "style": "page/size"},
        {"params": "?offset=0&limit=5", "style": "offset/limit"},
        {"params": "?skip=0&take=5", "style": "skip/take"},
        {"params": "", "style": "none"},
    ]
    
    for test in pagination_tests:
        url = f"{base_url.rstrip('/')}{endpoint}{test['params']}"
        test_result = {
            "style": test["style"],
            "url": url,
            "success": False,
            "response": None,
        }
        
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if 200 <= response.status < 300:
                    body = response.read().decode("utf-8")
                    data = json.loads(body)
                    test_result["success"] = True
                    
                    # Check if response structure indicates pagination
                    if isinstance(data, dict):
                        has_meta = any(k in data for k in ["total", "page", "pages", "count", "next", "previous"])
                        has_items = any(k in data for k in ["items", "data", "results"])
                        
                        if has_meta and has_items:
                            result["supports_pagination"] = True
                            result["pagination_style"] = test["style"]
                            test_result["response"] = {
                                "keys": list(data.keys()),
                                "has_meta": has_meta,
                                "has_items": has_items,
                            }
                    elif isinstance(data, list) and test["style"] != "none":
                        # Array response with pagination params might still work
                        test_result["response"] = {"type": "array", "count": len(data)}
                        
        except Exception as e:
            test_result["error"] = str(e)
            
        result["tests"].append(test_result)
    
    return result
