"""
Lambda Handler for Bedrock Agent Action Group - DevOps Operations

This Lambda is invoked by Bedrock Agent when user asks ops-related questions.
The agent decides which action to call based on the OpenAPI schema.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError


# ==============================================================================
# Configuration from Environment
# ==============================================================================
REGION = os.getenv("AWS_REGION", "us-east-1")
ASG_NAME = os.getenv("OPS_ASG_NAME", "")
TARGET_GROUP_ARN = os.getenv("OPS_TARGET_GROUP_ARN", "")
ALB_ARN = os.getenv("OPS_ALB_ARN", "")
DDB_TABLES = os.getenv("OPS_DDB_TABLES", "").split(",")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LOG_GROUPS = [g.strip() for g in os.getenv("OPS_LOG_GROUPS", "").split(",") if g.strip()]


# ==============================================================================
# AWS Clients
# ==============================================================================
def _asg_client():
    return boto3.client("autoscaling", region_name=REGION)

def _elbv2_client():
    return boto3.client("elbv2", region_name=REGION)

def _cloudwatch_client():
    return boto3.client("cloudwatch", region_name=REGION)

def _dynamodb_client():
    return boto3.client("dynamodb", region_name=REGION)

def _logs_client():
    return boto3.client("logs", region_name=REGION)


# ==============================================================================
# Action: Get Infrastructure Snapshot
# ==============================================================================
def get_infrastructure_snapshot(
    asg_name: Optional[str] = None,
    include_scaling_activities: bool = True,
) -> Dict[str, Any]:
    """
    Get real-time snapshot of AWS infrastructure (ASG, ALB, Target Group).
    
    Args:
        asg_name: Auto Scaling Group name (uses default if not provided)
        include_scaling_activities: Whether to include recent scaling activities
    
    Returns:
        Infrastructure snapshot with ASG, ALB, TG status
    """
    asg_name = asg_name or ASG_NAME
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": REGION,
        "api_base_url": API_BASE_URL,  # For check_api_health/check_api_pagination
        "asg": None,
        "target_group": None,
        "alb": None,
        "instance_refresh": None,
        "scaling_activities": [],
        "errors": {},
    }
    
    # Get ASG info
    if asg_name:
        try:
            asg = _asg_client()
            resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
            if resp.get("AutoScalingGroups"):
                asg_data = resp["AutoScalingGroups"][0]
                instances = asg_data.get("Instances", [])
                result["asg"] = {
                    "name": asg_name,
                    "desired_capacity": asg_data.get("DesiredCapacity"),
                    "min_size": asg_data.get("MinSize"),
                    "max_size": asg_data.get("MaxSize"),
                    "instance_count": len(instances),
                    "health_counts": _count_by_key(instances, "HealthStatus"),
                    "lifecycle_counts": _count_by_key(instances, "LifecycleState"),
                }
                
                # Get instance refresh status
                try:
                    ir_resp = asg.describe_instance_refreshes(
                        AutoScalingGroupName=asg_name,
                        MaxRecords=1,
                    )
                    if ir_resp.get("InstanceRefreshes"):
                        ir = ir_resp["InstanceRefreshes"][0]
                        result["instance_refresh"] = {
                            "status": ir.get("Status"),
                            "percentage_complete": ir.get("PercentageComplete", 0),
                            "start_time": ir.get("StartTime", "").isoformat() if ir.get("StartTime") else None,
                        }
                except Exception as e:
                    result["errors"]["instance_refresh"] = str(e)
                
                # Get scaling activities
                if include_scaling_activities:
                    try:
                        act_resp = asg.describe_scaling_activities(
                            AutoScalingGroupName=asg_name,
                            MaxRecords=10,
                        )
                        result["scaling_activities"] = [
                            {
                                "status": act.get("StatusCode"),
                                "description": act.get("Description", "")[:100],
                                "cause": act.get("Cause", "")[:100],
                            }
                            for act in act_resp.get("Activities", [])[:5]
                        ]
                    except Exception as e:
                        result["errors"]["scaling_activities"] = str(e)
                        
        except Exception as e:
            result["errors"]["asg"] = str(e)
    
    # Get Target Group info
    if TARGET_GROUP_ARN:
        try:
            elbv2 = _elbv2_client()
            resp = elbv2.describe_target_health(TargetGroupArn=TARGET_GROUP_ARN)
            targets = resp.get("TargetHealthDescriptions", [])
            result["target_group"] = {
                "arn": TARGET_GROUP_ARN,
                "target_count": len(targets),
                "health_counts": _count_by_nested_key(targets, "TargetHealth", "State"),
            }
        except Exception as e:
            result["errors"]["target_group"] = str(e)
    
    # Get ALB info
    if ALB_ARN:
        try:
            elbv2 = _elbv2_client()
            resp = elbv2.describe_load_balancers(LoadBalancerArns=[ALB_ARN])
            if resp.get("LoadBalancers"):
                alb = resp["LoadBalancers"][0]
                result["alb"] = {
                    "name": alb.get("LoadBalancerName"),
                    "dns_name": alb.get("DNSName"),
                    "state": alb.get("State", {}).get("Code"),
                    "type": alb.get("Type"),
                    "scheme": alb.get("Scheme"),
                }
        except Exception as e:
            result["errors"]["alb"] = str(e)
    
    return result


# ==============================================================================
# Action: Get DynamoDB Metrics
# ==============================================================================
def get_dynamodb_metrics(
    table_names: Optional[List[str]] = None,
    minutes: int = 10,
) -> Dict[str, Any]:
    """
    Get DynamoDB performance metrics from CloudWatch.
    
    Args:
        table_names: List of table names (uses defaults if not provided)
        minutes: Time window in minutes
    
    Returns:
        Metrics for each table including RCU, WCU, throttling
    """
    tables = table_names or [t.strip() for t in DDB_TABLES if t.strip()]
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "window_minutes": minutes,
        "tables": {},
    }
    
    cw = _cloudwatch_client()
    ddb = _dynamodb_client()
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=minutes)
    
    metrics_to_fetch = [
        "ConsumedReadCapacityUnits",
        "ConsumedWriteCapacityUnits",
        "ReadThrottleEvents",
        "WriteThrottleEvents",
        "ThrottledRequests",
    ]
    
    for table_name in tables:
        table_result = {
            "metrics": {},
            "billing_mode": "UNKNOWN",
            "provisioned_throughput": None,
        }
        
        # Get CloudWatch metrics
        for metric_name in metrics_to_fetch:
            try:
                resp = cw.get_metric_statistics(
                    Namespace="AWS/DynamoDB",
                    MetricName=metric_name,
                    Dimensions=[{"Name": "TableName", "Value": table_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=60,
                    Statistics=["Sum", "Average", "Maximum"],
                )
                datapoints = resp.get("Datapoints", [])
                if datapoints:
                    table_result["metrics"][metric_name] = {
                        "sum": sum(d.get("Sum", 0) for d in datapoints),
                        "average": sum(d.get("Average", 0) for d in datapoints) / len(datapoints),
                        "maximum": max(d.get("Maximum", 0) for d in datapoints),
                    }
                else:
                    table_result["metrics"][metric_name] = {"sum": 0, "average": 0, "maximum": 0}
            except Exception as e:
                table_result["metrics"][metric_name] = {"error": str(e)}
        
        # Get table description for billing mode
        try:
            desc = ddb.describe_table(TableName=table_name)
            table_info = desc.get("Table", {})
            billing = table_info.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
            table_result["billing_mode"] = billing
            
            if billing == "PROVISIONED":
                pt = table_info.get("ProvisionedThroughput", {})
                table_result["provisioned_throughput"] = {
                    "read": pt.get("ReadCapacityUnits", 0),
                    "write": pt.get("WriteCapacityUnits", 0),
                }
        except Exception as e:
            table_result["error"] = str(e)
        
        result["tables"][table_name] = table_result
    
    return result


# ============================================================================== 
# Action: Query CloudWatch Logs (Insights)
# ============================================================================== 
def query_cloudwatch_logs(
    log_group_names: Optional[List[str]] = None,
    minutes: int = 15,
    query: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Run a CloudWatch Logs Insights query over one or more log groups.

    This is a building block for RCA (e.g., finding exceptions around 5xx windows).

    Args:
        log_group_names: list of log group names (uses OPS_LOG_GROUPS env if not provided)
        minutes: lookback window
        query: Insights query string. If omitted, uses a safe default for errors/exceptions.
        limit: max number of returned rows (Insights applies limit)

    Returns:
        Query results (raw rows) plus a small summary.
    """
    groups = log_group_names or LOG_GROUPS
    if not groups:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "region": REGION,
            "error": "No log groups provided. Provide log_group_names or set OPS_LOG_GROUPS.",
        }

    minutes = max(1, int(minutes))
    limit = max(1, min(int(limit), 200))

    def _build_default_query(max_rows: int) -> str:
        # IMPORTANT: use word-boundary for 5xx so we don't match ports like ":50694".
        # Also match structured logs containing "status_code": 5xx.
        return (
            "fields @timestamp, @logStream, @message\n"
            "| filter @message like /ERROR|Exception|Traceback|\\\\b5\\\\d{2}\\\\b|\\\\\"status_code\\\\\":5\\\\d{2}/\n"
            "| sort @timestamp desc\n"
            f"| limit {max_rows}"
        )

    def _coerce_to_insights_query(q: Optional[str], max_rows: int) -> str:
        if not q or not str(q).strip():
            return _build_default_query(max_rows)
        s = str(q).strip()
        # If it already looks like an Insights query, pass through.
        if "|" in s or s.lstrip().startswith("fields ") or s.lstrip().startswith("filter "):
            return s

        # Otherwise, treat it like a simple search expression (e.g., "ERROR OR Exception OR 5xx").
        upper = s.upper()
        tokens: List[str] = []
        for part in upper.replace("|", " OR ").split(" OR "):
            t = part.strip()
            if not t:
                continue
            tokens.append(t)

        # Map user-friendly tokens to regex alternatives.
        alts: List[str] = []
        for t in tokens:
            if t in {"5XX", "5XXS", "5XX_ERRORS", "5XX ERROR", "5XX ERRORS"} or "5XX" in t:
                alts.append("\\\\b5\\\\d{2}\\\\b")
                alts.append("\\\\\"status_code\\\\\":5\\\\d{2}")
                continue
            if t in {"ERROR", "EXCEPTION", "TRACEBACK"}:
                alts.append(t.capitalize() if t != "ERROR" else "ERROR")
                continue
            # Fallback: use raw token; keep it safe-ish by stripping slashes.
            alts.append(t.replace("/", ""))

        # Ensure we always have something meaningful.
        if not alts:
            return _build_default_query(max_rows)

        regex = "|".join(alts)
        return (
            "fields @timestamp, @logStream, @message\n"
            f"| filter @message like /{regex}/\n"
            "| sort @timestamp desc\n"
            f"| limit {max_rows}"
        )

    query_string = _coerce_to_insights_query(query, limit)

    end_time = int(time.time())
    start_time = end_time - (minutes * 60)

    logs = _logs_client()
    start_resp = logs.start_query(
        logGroupNames=groups,
        startTime=start_time,
        endTime=end_time,
        queryString=query_string,
        limit=limit,
    )
    query_id = start_resp.get("queryId")

    # Poll results (keep within Lambda timeout)
    deadline = time.time() + 20
    status = "Running"
    results = []
    stats = {}
    while time.time() < deadline:
        resp = logs.get_query_results(queryId=query_id)
        status = resp.get("status", status)
        stats = resp.get("statistics", stats) or stats
        if status in {"Complete", "Failed", "Cancelled", "Timeout"}:
            results = resp.get("results", []) or []
            break
        time.sleep(0.6)

    summary = {
        "status": status,
        "row_count": len(results),
        "log_groups": groups,
        "minutes": minutes,
        "query_id": query_id,
    }

    # Extract a tiny signal: top 5 message prefixes
    message_samples: List[str] = []
    for row in results[:20]:
        for cell in row:
            if cell.get("field") == "@message":
                msg = (cell.get("value") or "").strip().replace("\n", " ")
                if msg:
                    message_samples.append(msg[:160])
                break

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": REGION,
        "summary": summary,
        "statistics": stats,
        "results": results,
        "message_samples": message_samples,
    }


# ============================================================================== 
# Action: Get Infra Metrics (ALB/TG)
# ============================================================================== 
def get_infra_metrics(
    minutes: int = 15,
    period_seconds: int = 60,
) -> Dict[str, Any]:
    """Get CloudWatch metrics for ALB + Target Group over a recent window.

    Focuses on operational signals used in incident triage:
    - ALB 5xx
    - Target 5xx
    - Target response time
    - Healthy/Unhealthy host counts
    - Request count
    """

    def _arn_suffix(arn: str, prefix: str) -> str:
        if not arn:
            return ""
        marker = f"{prefix}/"
        i = arn.find(marker)
        if i == -1:
            return ""
        return arn[i + len(marker):]

    def _summarize_series(timestamps: List[datetime], values: List[float]) -> Dict[str, Any]:
        if not timestamps or not values:
            return {"points": [], "summary": {"count": 0}}
        pairs = list(zip(timestamps, values))
        pairs.sort(key=lambda x: x[0])
        vals = [v for _, v in pairs]
        latest_ts, latest_val = pairs[-1]
        summary = {
            "count": len(vals),
            "sum": float(sum(vals)),
            "avg": float(sum(vals) / len(vals)),
            "max": float(max(vals)),
            "latest": {"timestamp": latest_ts.isoformat(), "value": float(latest_val)},
        }
        points = [{"timestamp": ts.isoformat(), "value": float(v)} for ts, v in pairs[-20:]]
        return {"points": points, "summary": summary}

    minutes = max(1, int(minutes))
    period_seconds = max(60, int(period_seconds))

    lb_dim = _arn_suffix(ALB_ARN, "loadbalancer")
    tg_dim = _arn_suffix(TARGET_GROUP_ARN, "targetgroup")

    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)

    cw = _cloudwatch_client()

    metric_queries: List[Dict[str, Any]] = []

    def _add_query(qid: str, metric_name: str, stat: str, dimensions: List[Dict[str, str]]):
        metric_queries.append(
            {
                "Id": qid,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/ApplicationELB",
                        "MetricName": metric_name,
                        "Dimensions": dimensions,
                    },
                    "Period": period_seconds,
                    "Stat": stat,
                },
                "ReturnData": True,
            }
        )

    dims_lb = [{"Name": "LoadBalancer", "Value": lb_dim}] if lb_dim else []
    dims_tg = (
        [{"Name": "LoadBalancer", "Value": lb_dim}, {"Name": "TargetGroup", "Value": tg_dim}]
        if lb_dim and tg_dim
        else []
    )

    errors: Dict[str, str] = {}
    if not lb_dim:
        errors["alb"] = "OPS_ALB_ARN is missing or invalid; cannot derive LoadBalancer dimension."
    if not tg_dim:
        errors["target_group"] = "OPS_TARGET_GROUP_ARN is missing or invalid; cannot derive TargetGroup dimension."

    if dims_lb:
        _add_query("alb_5xx", "HTTPCode_ELB_5XX_Count", "Sum", dims_lb)
        _add_query("alb_req", "RequestCount", "Sum", dims_lb)

    if dims_tg:
        _add_query("tg_5xx", "HTTPCode_Target_5XX_Count", "Sum", dims_tg)
        _add_query("tg_latency", "TargetResponseTime", "Average", dims_tg)
        _add_query("tg_healthy", "HealthyHostCount", "Average", dims_tg)
        _add_query("tg_unhealthy", "UnHealthyHostCount", "Average", dims_tg)

    if not metric_queries:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "region": REGION,
            "window_minutes": minutes,
            "period_seconds": period_seconds,
            "dimensions": {"load_balancer": lb_dim, "target_group": tg_dim},
            "errors": errors or {"metrics": "No valid dimensions available to query metrics."},
        }

    resp = cw.get_metric_data(
        MetricDataQueries=metric_queries,
        StartTime=start,
        EndTime=end,
        ScanBy="TimestampAscending",
        MaxDatapoints=500,
    )

    metrics: Dict[str, Any] = {}
    for r in resp.get("MetricDataResults", []) or []:
        metrics[r.get("Id", "unknown")] = _summarize_series(r.get("Timestamps", []) or [], r.get("Values", []) or [])

    # Add hints for metrics with no data
    no_data_hints: Dict[str, str] = {}
    for metric_id in ["tg_5xx", "tg_latency", "tg_healthy", "tg_unhealthy", "alb_5xx", "alb_req"]:
        if metric_id in metrics and metrics[metric_id].get("summary", {}).get("count", 0) == 0:
            if metric_id in ["tg_latency", "tg_healthy", "tg_unhealthy"]:
                no_data_hints[metric_id] = "0 datapoints - có thể do ít traffic hoặc TG chưa có request trong cửa sổ này."
            elif "5xx" in metric_id:
                no_data_hints[metric_id] = "0 datapoints - không có lỗi 5xx trong cửa sổ này (tốt)."

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": REGION,
        "window_minutes": minutes,
        "period_seconds": period_seconds,
        "dimensions": {"load_balancer": lb_dim, "target_group": tg_dim},
        "metrics": metrics,
        "no_data_hints": no_data_hints,
        "errors": errors,
    }


# ==============================================================================
# Action: Get CloudWatch Alarms
# ==============================================================================
def get_cloudwatch_alarms(
    alarm_name_prefix: Optional[str] = None,
    state_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get status of CloudWatch alarms for incident detection.
    
    Args:
        alarm_name_prefix: Filter alarms by name prefix (e.g., "course-management")
        state_filter: Filter by state: ALARM, OK, INSUFFICIENT_DATA (default: all)
    
    Returns:
        List of alarms with their current state and recent state changes
    """
    cw = _cloudwatch_client()
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": REGION,
        "alarms": [],
        "summary": {"ALARM": 0, "OK": 0, "INSUFFICIENT_DATA": 0},
        "errors": {},
    }
    
    try:
        # Build request params
        params: Dict[str, Any] = {"MaxRecords": 100}
        if alarm_name_prefix:
            params["AlarmNamePrefix"] = alarm_name_prefix
        if state_filter and state_filter.upper() in ["ALARM", "OK", "INSUFFICIENT_DATA"]:
            params["StateValue"] = state_filter.upper()
        
        resp = cw.describe_alarms(**params)
        
        for alarm in resp.get("MetricAlarms", []) or []:
            state = alarm.get("StateValue", "UNKNOWN")
            result["summary"][state] = result["summary"].get(state, 0) + 1
            
            result["alarms"].append({
                "name": alarm.get("AlarmName"),
                "state": state,
                "state_reason": (alarm.get("StateReason") or "")[:200],
                "state_updated": alarm.get("StateUpdatedTimestamp", "").isoformat() if alarm.get("StateUpdatedTimestamp") else None,
                "metric_name": alarm.get("MetricName"),
                "namespace": alarm.get("Namespace"),
                "threshold": alarm.get("Threshold"),
                "comparison": alarm.get("ComparisonOperator"),
            })
        
        # Also get composite alarms
        for alarm in resp.get("CompositeAlarms", []) or []:
            state = alarm.get("StateValue", "UNKNOWN")
            result["summary"][state] = result["summary"].get(state, 0) + 1
            
            result["alarms"].append({
                "name": alarm.get("AlarmName"),
                "state": state,
                "state_reason": (alarm.get("StateReason") or "")[:200],
                "state_updated": alarm.get("StateUpdatedTimestamp", "").isoformat() if alarm.get("StateUpdatedTimestamp") else None,
                "type": "composite",
            })
            
    except Exception as e:
        result["errors"]["describe_alarms"] = str(e)
    
    return result


# ==============================================================================
# Action: Plan Instance Refresh
# ==============================================================================
def plan_instance_refresh(
    asg_name: Optional[str] = None,
    min_healthy_percentage: int = 90,
    instance_warmup: int = 60,
) -> Dict[str, Any]:
    """
    Create a plan for ASG instance refresh with real validation (does not execute).
    
    Args:
        asg_name: Auto Scaling Group name
        min_healthy_percentage: Minimum healthy instances during refresh
        instance_warmup: Seconds to wait after instance launch
    
    Returns:
        Instance refresh plan details with validation
    """
    asg_name = asg_name or ASG_NAME
    
    if not asg_name:
        return {
            "action": "plan_instance_refresh",
            "status": "error",
            "error": "ASG name is required. Set OPS_ASG_NAME or provide asg_name.",
        }
    
    result = {
        "action": "plan_instance_refresh",
        "asg_name": asg_name,
        "strategy": "Rolling",
        "preferences": {
            "MinHealthyPercentage": min_healthy_percentage,
            "InstanceWarmup": instance_warmup,
        },
        "status": "planned",
        "validation": {},
        "risks": [],
        "note": "This is a plan only. Use execute_instance_refresh to start.",
    }
    
    # Validate current ASG state
    try:
        asg = _asg_client()
        
        # Check ASG exists and get current state
        resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
        if not resp.get("AutoScalingGroups"):
            result["status"] = "error"
            result["error"] = f"ASG '{asg_name}' not found."
            return result
        
        asg_data = resp["AutoScalingGroups"][0]
        instances = asg_data.get("Instances", [])
        desired = asg_data.get("DesiredCapacity", 0)
        healthy_count = sum(1 for i in instances if i.get("HealthStatus") == "Healthy")
        in_service_count = sum(1 for i in instances if i.get("LifecycleState") == "InService")
        
        result["validation"]["current_state"] = {
            "desired_capacity": desired,
            "total_instances": len(instances),
            "healthy_instances": healthy_count,
            "in_service_instances": in_service_count,
        }
        
        # Check for ongoing instance refresh
        ir_resp = asg.describe_instance_refreshes(
            AutoScalingGroupName=asg_name,
            MaxRecords=1,
        )
        if ir_resp.get("InstanceRefreshes"):
            ir = ir_resp["InstanceRefreshes"][0]
            ir_status = ir.get("Status", "")
            if ir_status in ["Pending", "InProgress", "Cancelling"]:
                result["status"] = "blocked"
                result["validation"]["ongoing_refresh"] = {
                    "status": ir_status,
                    "percentage_complete": ir.get("PercentageComplete", 0),
                    "start_time": ir.get("StartTime", "").isoformat() if ir.get("StartTime") else None,
                }
                result["risks"].append("Có instance refresh đang chạy. Không thể start refresh mới.")
                return result
            
            result["validation"]["last_refresh"] = {
                "status": ir_status,
                "percentage_complete": ir.get("PercentageComplete", 0),
                "end_time": ir.get("EndTime", "").isoformat() if ir.get("EndTime") else None,
            }
        
        # Calculate impact
        min_healthy_required = int(desired * min_healthy_percentage / 100)
        max_replace_at_once = desired - min_healthy_required
        
        result["validation"]["impact"] = {
            "min_healthy_required": min_healthy_required,
            "max_replace_at_once": max(1, max_replace_at_once),
            "estimated_waves": max(1, (desired + max_replace_at_once - 1) // max(1, max_replace_at_once)) if max_replace_at_once > 0 else desired,
            "estimated_duration_minutes": max(1, max_replace_at_once) * (instance_warmup // 60 + 2) if desired > 0 else 0,
        }
        
        # Risk assessment
        if healthy_count < desired:
            result["risks"].append(f"Chỉ có {healthy_count}/{desired} instances healthy. Refresh có thể gây service degradation.")
        if min_healthy_percentage < 50:
            result["risks"].append("min_healthy_percentage < 50% rất rủi ro, có thể gây downtime.")
        if desired <= 1:
            result["risks"].append("Chỉ có 1 instance. Refresh SẼ gây downtime ngắn.")
        
        if not result["risks"]:
            result["risks"].append("Không phát hiện rủi ro lớn. Có thể proceed nếu cần.")
            
    except Exception as e:
        result["validation"]["error"] = str(e)
        result["risks"].append(f"Không thể validate ASG: {str(e)}")
    
    return result


# ==============================================================================
# Action: Execute Instance Refresh
# ==============================================================================
def execute_instance_refresh(
    asg_name: Optional[str] = None,
    min_healthy_percentage: int = 90,
    instance_warmup: int = 60,
) -> Dict[str, Any]:
    """
    Execute ASG instance refresh (rolling deployment).
    
    Args:
        asg_name: Auto Scaling Group name
        min_healthy_percentage: Minimum healthy instances during refresh
        instance_warmup: Seconds to wait after instance launch
    
    Returns:
        Instance refresh execution result
    """
    asg_name = asg_name or ASG_NAME
    
    if not asg_name:
        return {
            "success": False,
            "error": "ASG name is required. Set OPS_ASG_NAME or provide asg_name.",
        }
    
    try:
        asg = _asg_client()
        resp = asg.start_instance_refresh(
            AutoScalingGroupName=asg_name,
            Strategy="Rolling",
            Preferences={
                "MinHealthyPercentage": min_healthy_percentage,
                "InstanceWarmup": instance_warmup,
            },
        )
        
        return {
            "success": True,
            "asg_name": asg_name,
            "instance_refresh_id": resp.get("InstanceRefreshId"),
            "status": "started",
        }
    except ClientError as e:
        return {
            "success": False,
            "asg_name": asg_name,
            "error": e.response.get("Error", {}).get("Message", str(e)),
        }


# ==============================================================================
# Action: Check API Health
# ==============================================================================
def check_api_health(
    base_url: Optional[str] = None,
    endpoints: Optional[List[str]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    Check health of API endpoints.
    
    Args:
        base_url: Base URL of the API
        endpoints: List of endpoints to check
        timeout: Request timeout in seconds
    
    Returns:
        Health status for each endpoint
    """
    base_url = base_url or API_BASE_URL
    endpoints = endpoints or ["/health", "/api/courses", "/api/students", "/api/enrollments"]
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "endpoints": {},
        "summary": {"healthy": 0, "unhealthy": 0},
    }
    
    for endpoint in endpoints:
        url = f"{base_url.rstrip('/')}{endpoint}"
        ep_result = {
            "url": url,
            "healthy": False,
            "status_code": None,
            "response_time_ms": None,
            "error": None,
        }
        
        try:
            start = time.time()
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                elapsed = (time.time() - start) * 1000
                ep_result["status_code"] = resp.status
                ep_result["response_time_ms"] = round(elapsed, 2)
                ep_result["healthy"] = 200 <= resp.status < 300
                
        except urllib.error.HTTPError as e:
            ep_result["status_code"] = e.code
            ep_result["error"] = str(e.reason)
        except urllib.error.URLError as e:
            ep_result["error"] = f"Connection failed: {e.reason}"
        except Exception as e:
            ep_result["error"] = str(e)
        
        if ep_result["healthy"]:
            result["summary"]["healthy"] += 1
        else:
            result["summary"]["unhealthy"] += 1
        
        result["endpoints"][endpoint] = ep_result
    
    return result


# ==============================================================================
# Action: Baseline Check All (Composite)
# ==============================================================================
def get_baseline_check_all(minutes: int = 15) -> Dict[str, Any]:
    """
    Comprehensive baseline check - calls multiple tools and aggregates results.
    This is a composite action that internally calls:
    - get_infrastructure_snapshot
    - get_cloudwatch_alarms
    - get_infra_metrics
    - get_dynamodb_metrics
    
    Args:
        minutes: Time window for metrics (default 15)
    
    Returns:
        Aggregated baseline check with all system status
    """
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "window_minutes": minutes,
        "infrastructure": {},
        "alarms": {},
        "metrics": {},
        "dynamodb": {},
        "overall_health": "unknown",
        "issues": [],
    }
    
    try:
        # 1. Infrastructure snapshot
        result["infrastructure"] = get_infrastructure_snapshot(include_scaling_activities=True)
        
        # 2. CloudWatch alarms
        result["alarms"] = get_cloudwatch_alarms()
        
        # 3. ALB/TG metrics
        result["metrics"] = get_infra_metrics(minutes=minutes)
        
        # 4. DynamoDB metrics
        result["dynamodb"] = get_dynamodb_metrics(minutes=minutes)
        
        # Assess overall health
        issues = []
        
        # Check for unhealthy instances
        if result["infrastructure"].get("target_group", {}).get("health_counts", {}).get("unhealthy", 0) > 0:
            issues.append("Unhealthy targets detected")
        
        # Check for alarms
        alarms_in_alarm = result["alarms"].get("summary", {}).get("ALARM", 0)
        if alarms_in_alarm > 0:
            issues.append(f"{alarms_in_alarm} alarms in ALARM state")
        
        # Check for 5xx errors
        metrics_summary = result["metrics"].get("summary", {})
        alb_5xx = metrics_summary.get("alb_5xx", {}).get("sum", 0)
        if alb_5xx > 0:
            issues.append(f"{alb_5xx} ALB 5xx errors detected")
        
        result["issues"] = issues
        result["overall_health"] = "unhealthy" if issues else "healthy"
        
    except Exception as e:
        result["error"] = str(e)
        result["overall_health"] = "error"
    
    return result


# ==============================================================================
# Action: Get Latest HTTP 5xx (Structured)
# ==============================================================================
def get_latest_http_5xx(
    minutes: int = 180,
    limit: int = 20,
    log_group_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Find the most recent HTTP 5xx (including 500) in CloudWatch Logs.

    Designed for: "có lỗi 500/5xx nào gần đây nhất" / "chi tiết lỗi 500".
    Uses a minimal Logs Insights query (fields/filter/sort/limit only), then parses
    common access log formats in Python to produce structured output.
    """

    minutes = max(1, int(minutes))
    limit = max(1, min(int(limit), 200))

    groups = log_group_names or LOG_GROUPS
    if not groups:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "region": REGION,
            "window_minutes": minutes,
            "error": "No log groups provided. Provide log_group_names or set OPS_LOG_GROUPS.",
        }

    # Filter for 5xx status codes in structured JSON logs:
    # - "status_code": 5xx (app http_access logs)
    # - "status_code": 5xx (ALB alb_access logs)  
    # - "elb_status_code": 5xx (ALB logs alternative field)
    query = (
        "fields @timestamp, @logStream, @message\n"
        '| filter @message like /"status_code":\\s*5\\d{2}/ '
        'or @message like /"elb_status_code":\\s*5\\d{2}/\n'
        "| sort @timestamp desc\n"
        f"| limit {limit}"
    )

    primary = query_cloudwatch_logs(
        log_group_names=groups,
        minutes=minutes,
        query=query,
        limit=limit,
    )

    access_re = re.compile(r'"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+HTTP/[^\"]+"\s+(?P<status>\d{3})')

    def _try_parse_json(msg: str) -> Optional[Dict[str, Any]]:
        i = msg.find("{")
        if i == -1:
            return None
        try:
            obj = json.loads(msg[i:])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    def _extract(ts: Optional[str], log_stream: Optional[str], msg: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "timestamp": ts,
            "log_stream": log_stream,
            "status_code": None,
            "method": None,
            "path": None,
            "latency_ms": None,
            "request_id": None,
            "instance_id": None,
            "message": msg,
        }

        if not msg:
            return out

        # Normalize escaped quotes if present.
        normalized = msg.replace('\\"', '"')

        js = _try_parse_json(normalized)
        # Support both app logs (http_access) and ALB logs (alb_access)
        if js and ("status_code" in js or js.get("log_type") in ("http_access", "alb_access")):
            try:
                status_val = js.get("status_code")
                if status_val is not None:
                    out["status_code"] = int(status_val)
            except Exception:
                out["status_code"] = None
            out["method"] = js.get("method")
            out["path"] = js.get("path")
            out["request_id"] = js.get("request_id") or js.get("trace_id")  # ALB uses trace_id
            out["instance_id"] = js.get("instance_id") or js.get("target_ip")  # ALB uses target_ip
            # ALB logs include error_reason for debugging
            if js.get("error_reason"):
                out["error_reason"] = js.get("error_reason")
            if js.get("client_ip"):
                out["client_ip"] = js.get("client_ip")
            try:
                latency_val = js.get("latency_ms")
                if latency_val is not None:
                    out["latency_ms"] = float(latency_val)
            except Exception:
                out["latency_ms"] = js.get("latency_ms")
            return out

        m = access_re.search(normalized)
        if m:
            try:
                out["status_code"] = int(m.group("status"))
            except Exception:
                out["status_code"] = None
            out["method"] = m.group("method")
            out["path"] = m.group("path")
            return out

        # Fallback: best-effort 5xx extraction
        m2 = re.search(r"\b(5\d{2})\b", normalized)
        if m2:
            try:
                out["status_code"] = int(m2.group(1))
            except Exception:
                pass
        return out

    def _row_to_dict(row: List[Dict[str, str]]) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for cell in row or []:
            f = cell.get("field")
            if not f:
                continue
            d[f] = cell.get("value")
        return _extract(d.get("@timestamp"), d.get("@logStream"), (d.get("@message") or ""))

    entries = [_row_to_dict(r) for r in (primary.get("results") or [])]
    entries = [e for e in entries if isinstance(e.get("status_code"), int) and 500 <= int(e["status_code"]) <= 599]

    # Prefer the newest structured entry that has a request_id (typically the
    # app's JSON http_access log), so we can return latency/instance correlation.
    latest = next((e for e in entries if e.get("request_id")), (entries[0] if entries else None))

    related: Dict[str, Any] = {}
    if latest and latest.get("request_id"):
        rid = str(latest["request_id"]).strip()
        if rid:
            rid_safe = re.sub(r"[^A-Za-z0-9._:-]", "", rid)
            related_query = (
                "fields @timestamp, @logStream, @message\n"
                f"| filter @message like /{rid_safe}/\n"
                "| sort @timestamp asc\n"
                "| limit 50"
            )
            related["request_id"] = rid
            related["logs"] = query_cloudwatch_logs(
                log_group_names=groups,
                minutes=minutes,
                query=related_query,
                limit=50,
            )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": REGION,
        "window_minutes": minutes,
        "log_groups": groups,
        "latest": latest,
        "candidates_checked": len(entries),
        "related": related,
        "raw": {
            "summary": primary.get("summary"),
            "statistics": primary.get("statistics"),
        },
    }


# ==============================================================================
# Action: Get 5xx with Root Cause Analysis (RCA)
# ==============================================================================
def get_5xx_root_cause_analysis(
    minutes: int = 60,
    include_infra_check: bool = True,
) -> Dict[str, Any]:
    """
    Find recent 5xx errors AND automatically analyze root cause.
    
    This is the SMART version that:
    1. Finds the latest 5xx error
    2. Explains what the error code means
    3. Checks infrastructure health (ASG, Target Group)
    4. Correlates with metrics and logs
    5. Provides actionable root cause and suggestions
    
    Designed for: "Tại sao có lỗi 5xx?" / "Phân tích lỗi 500 gần đây"
    """
    
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "region": REGION,
        "window_minutes": minutes,
        "error_found": False,
        "error_details": None,
        "root_cause_analysis": None,
        "infrastructure_state": None,
        "recommendations": [],
    }
    
    # Step 1: Find latest 5xx error
    error_data = get_latest_http_5xx(minutes=minutes, limit=10)
    latest = error_data.get("latest")
    
    if not latest or not latest.get("status_code"):
        result["error_found"] = False
        result["root_cause_analysis"] = {
            "summary": f"Không tìm thấy lỗi 5xx trong {minutes} phút gần đây.",
            "status": "OK"
        }
        return result
    
    result["error_found"] = True
    result["error_details"] = {
        "timestamp": latest.get("timestamp"),
        "status_code": latest.get("status_code"),
        "method": latest.get("method"),
        "path": latest.get("path"),
        "latency_ms": latest.get("latency_ms"),
        "client_ip": latest.get("client_ip"),
        "target_ip": latest.get("instance_id") or latest.get("target_ip"),
        "request_id": latest.get("request_id"),
        "error_reason": latest.get("error_reason"),
    }
    
    status_code = latest.get("status_code")
    error_reason = latest.get("error_reason")
    
    # Step 2: Analyze error code and determine root cause
    rca = {
        "error_type": None,
        "explanation": None,
        "likely_cause": None,
        "source": None,  # "ALB" or "Application"
        "severity": None,
        "affected_component": None,
    }
    
    # Error code analysis with Vietnamese explanations
    error_explanations = {
        500: {
            "type": "Internal Server Error",
            "source": "Application",
            "explanation": "Lỗi xảy ra bên trong ứng dụng (exception không được handle).",
            "likely_causes": [
                "Code có bug/exception",
                "Database connection failed", 
                "External API call failed",
                "Out of memory",
            ],
            "severity": "HIGH",
        },
        501: {
            "type": "Not Implemented",
            "source": "Application",
            "explanation": "Server không hỗ trợ chức năng được yêu cầu.",
            "likely_causes": ["API endpoint chưa được implement"],
            "severity": "MEDIUM",
        },
        502: {
            "type": "Bad Gateway",
            "source": "ALB",
            "explanation": "ALB không thể kết nối đến target (EC2 instance).",
            "likely_causes": [
                "EC2 instance đang shutdown/restart",
                "Application chưa start/crashed",
                "Security group block connection",
                "Target đang unhealthy",
            ],
            "severity": "CRITICAL",
        },
        503: {
            "type": "Service Unavailable",
            "source": "ALB",
            "explanation": "Không có target healthy nào để xử lý request.",
            "likely_causes": [
                "Tất cả EC2 instances đều unhealthy",
                "ASG đang scale down",
                "Deployment đang diễn ra",
                "Health check failing",
            ],
            "severity": "CRITICAL",
        },
        504: {
            "type": "Gateway Timeout",
            "source": "ALB",
            "explanation": "Target không phản hồi trong thời gian cho phép (timeout).",
            "likely_causes": [
                "Request xử lý quá lâu (> 60s mặc định)",
                "Application bị block/deadlock",
                "Database query chậm",
                "External API timeout",
                "CPU/Memory quá tải",
            ],
            "severity": "HIGH",
        },
    }
    
    error_info = error_explanations.get(status_code, {
        "type": f"HTTP {status_code}",
        "source": "Unknown",
        "explanation": f"Lỗi HTTP {status_code}",
        "likely_causes": ["Unknown"],
        "severity": "MEDIUM",
    })
    
    rca["error_type"] = error_info["type"]
    rca["source"] = error_info["source"]
    rca["explanation"] = error_info["explanation"]
    rca["severity"] = error_info["severity"]
    rca["likely_causes"] = error_info["likely_causes"]
    
    # Step 3: Check infrastructure if error is from ALB (502/503/504)
    infra_state = {}
    specific_cause = None
    
    if include_infra_check and status_code in (502, 503, 504):
        try:
            # Get ASG and Target Group status
            snapshot = get_infrastructure_snapshot(include_scaling_activities=True)
            
            asg_info = snapshot.get("asg", {})
            tg_info = snapshot.get("target_group", {})
            
            infra_state = {
                "asg": {
                    "name": asg_info.get("name"),
                    "desired": asg_info.get("desired_capacity"),
                    "running": asg_info.get("instance_count"),
                    "health_counts": asg_info.get("health_counts"),
                    "lifecycle_counts": asg_info.get("lifecycle_counts"),
                },
                "target_group": {
                    "healthy_count": tg_info.get("healthy_count", 0),
                    "unhealthy_count": tg_info.get("unhealthy_count", 0),
                    "targets": tg_info.get("targets", []),
                },
                "instance_refresh": snapshot.get("instance_refresh"),
                "recent_scaling": snapshot.get("scaling_activities", [])[:3],
            }
            
            # Determine specific cause based on infrastructure state
            healthy_targets = tg_info.get("healthy_count", 0)
            unhealthy_targets = tg_info.get("unhealthy_count", 0)
            refresh_status = (snapshot.get("instance_refresh") or {}).get("status")
            
            if status_code == 503 and healthy_targets == 0:
                specific_cause = "KHÔNG CÓ TARGET HEALTHY - Tất cả instances đều unhealthy hoặc đang trong quá trình khởi động."
                rca["affected_component"] = "Target Group"
                
            elif status_code == 502:
                if unhealthy_targets > 0:
                    specific_cause = f"CÓ {unhealthy_targets} TARGET UNHEALTHY - Instance có thể đang restart hoặc app crashed."
                    rca["affected_component"] = "EC2 Instances"
                elif refresh_status in ("Pending", "InProgress"):
                    specific_cause = "INSTANCE REFRESH ĐANG CHẠY - Deployment đang diễn ra, một số instance có thể unavailable."
                    rca["affected_component"] = "ASG Instance Refresh"
                else:
                    specific_cause = "Target không phản hồi - Kiểm tra application logs trên instance."
                    rca["affected_component"] = "Application"
                    
            elif status_code == 504:
                # Check if there's a pattern of slow requests
                specific_cause = "REQUEST TIMEOUT - Application xử lý quá lâu. Kiểm tra database queries, external API calls, hoặc CPU usage."
                rca["affected_component"] = "Application Performance"
                
        except Exception as e:
            infra_state["error"] = f"Không thể kiểm tra infrastructure: {str(e)}"
    
    elif status_code == 500:
        # For 500 errors, try to find stack trace
        specific_cause = "APPLICATION EXCEPTION - Cần xem stack trace trong logs để biết chi tiết."
        rca["affected_component"] = "Application Code"
        
        # Try to find related error logs
        if latest.get("request_id"):
            try:
                trace_query = f'fields @timestamp, @message | filter @message like "{latest["request_id"]}" | filter @message like /error|exception|traceback/i | limit 5'
                trace_logs = query_cloudwatch_logs(
                    log_group_names=LOG_GROUPS,
                    minutes=minutes,
                    query=trace_query,
                    limit=5,
                )
                if trace_logs.get("results"):
                    infra_state["stack_trace_found"] = True
                    infra_state["related_errors"] = [
                        r[2].get("value", "") if len(r) > 2 else "" 
                        for r in trace_logs.get("results", [])
                    ][:3]
            except Exception:
                pass
    
    rca["specific_cause"] = specific_cause
    result["root_cause_analysis"] = rca
    result["infrastructure_state"] = infra_state
    
    # Step 4: Generate recommendations
    recommendations = []
    
    if status_code == 500:
        recommendations = [
            f"1. Xem stack trace với request_id: {latest.get('request_id')}",
            "2. Kiểm tra application logs: query_cloudwatch_logs với filter error/exception",
            "3. Review code changes gần đây",
            "4. Kiểm tra database connectivity",
        ]
    elif status_code == 502:
        recommendations = [
            "1. Kiểm tra Target Group health: get_infrastructure_snapshot",
            "2. SSH vào instance kiểm tra app đang chạy: systemctl status app",
            "3. Xem application logs trên instance",
            "4. Kiểm tra security group rules",
        ]
    elif status_code == 503:
        recommendations = [
            "1. Kiểm tra ASG desired capacity và instance count",
            "2. Xem scaling activities gần đây",
            "3. Kiểm tra health check configuration",
            "4. Nếu cần, tăng desired capacity hoặc execute instance refresh",
        ]
    elif status_code == 504:
        recommendations = [
            "1. Kiểm tra metrics: get_infra_metrics để xem latency trend",
            "2. Profile slow database queries",
            "3. Tăng ALB timeout nếu cần (mặc định 60s)",
            "4. Kiểm tra external API dependencies",
            "5. Review CPU/Memory usage trên instances",
        ]
    
    result["recommendations"] = recommendations
    
    # Step 5: Generate summary in Vietnamese
    summary_parts = [
        f"🔴 Phát hiện lỗi {status_code} ({rca['error_type']})",
        f"📍 Nguồn: {rca['source']}",
        f"⏰ Thời điểm: {latest.get('timestamp')}",
        f"🎯 Endpoint: {latest.get('method')} {latest.get('path')}",
    ]
    
    if specific_cause:
        summary_parts.append(f"")
        summary_parts.append(f"💡 NGUYÊN NHÂN: {specific_cause}")
    
    if rca.get("affected_component"):
        summary_parts.append(f"🔧 Component ảnh hưởng: {rca['affected_component']}")
    
    result["summary"] = "\n".join(summary_parts)
    
    return result


# ==============================================================================
# Action: Check API Pagination
# ==============================================================================
def check_api_pagination(
    base_url: Optional[str] = None,
    endpoint: str = "/api/courses",
    timeout: int = 10,
) -> Dict[str, Any]:
    """Check if an API endpoint supports pagination."""
    base_url = base_url or API_BASE_URL

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": f"{base_url.rstrip('/')}{endpoint}",
        "supports_pagination": False,
        "pagination_style": None,
        "tests": [],
    }

    pagination_tests = [
        {"params": "?page=1&limit=5", "style": "page/limit"},
        {"params": "?page=1&size=5", "style": "page/size"},
        {"params": "?offset=0&limit=5", "style": "offset/limit"},
    ]

    for test in pagination_tests:
        url = f"{base_url.rstrip('/')}{endpoint}{test['params']}"
        test_result: Dict[str, Any] = {"style": test["style"], "success": False}

        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    body = resp.read().decode("utf-8")
                    data = json.loads(body)
                    test_result["success"] = True
                    if isinstance(data, dict):
                        has_meta = any(k in data for k in ["total", "page", "pages", "count"])
                        has_items = any(k in data for k in ["items", "data", "results"])
                        if has_meta and has_items:
                            result["supports_pagination"] = True
                            result["pagination_style"] = test["style"]
        except Exception as e:
            test_result["error"] = str(e)

        result["tests"].append(test_result)

    return result


# ==============================================================================
# Helper Functions
# ==============================================================================
def _count_by_key(items: List[Dict], key: str) -> Dict[str, int]:
    counts = {}
    for item in items:
        val = item.get(key, "Unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts

def _count_by_nested_key(items: List[Dict], outer: str, inner: str) -> Dict[str, int]:
    counts = {}
    for item in items:
        val = item.get(outer, {}).get(inner, "Unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


# ==============================================================================
# Lambda Handler - Bedrock Agent Action Group
# ==============================================================================
def lambda_handler(event, context):
    """
    Lambda handler for Bedrock Agent Action Group.
    
    Bedrock Agent sends events with:
    - actionGroup: Name of the action group
    - function: Name of the function to call
    - parameters: List of {name, value} pairs
    """
    # Extract action info from Bedrock Agent event
    # Bedrock can invoke Lambda in (at least) two shapes:
    # 1) API schema action groups: apiPath/httpMethod/parameters/requestBody
    # 2) Function details action groups: function/parameters
    action_group = event.get("actionGroup", "")
    api_path = event.get("apiPath") or event.get("path") or ""
    http_method = (event.get("httpMethod") or "").upper()
    function_name = event.get("function", "")
    parameters = event.get("parameters", [])
    
    def _coerce_scalar(val: Any) -> Any:
        if not isinstance(val, str):
            return val
        s = val.strip()
        if s == "":
            return val
        lowered = s.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        # Try JSON first (handles numbers, lists, objects)
        try:
            return json.loads(s)
        except Exception:
            pass
        # Try int/float
        try:
            return int(s)
        except Exception:
            pass
        try:
            return float(s)
        except Exception:
            return val

    # Convert parameters list to dict
    params: Dict[str, Any] = {}
    for p in parameters or []:
        name = p.get("name")
        if not name:
            continue
        value = _coerce_scalar(p.get("value"))
        params[name] = value

    # Merge requestBody (API schema mode) if present
    request_body = event.get("requestBody")
    if isinstance(request_body, dict):
        content = request_body.get("content")
        if isinstance(content, dict):
            for _ct, payload in content.items():
                if isinstance(payload, dict) and "body" in payload:
                    body_val = payload.get("body")
                    body_val = _coerce_scalar(body_val)
                    if isinstance(body_val, dict):
                        params.update(body_val)
                    break

    # Log a sanitized event summary (avoid logging raw inputs like queries/inputText)
    try:
        summary = {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method,
            "function": function_name,
            "parameterNames": sorted(list(params.keys())),
        }
        if "minutes" in params:
            summary["minutes"] = params.get("minutes")
        print(f"EventSummary: {json.dumps(summary)}")
    except Exception:
        # Never fail the request due to logging
        pass
    
    # Route to appropriate function
    action_functions = {
        "get_infrastructure_snapshot": get_infrastructure_snapshot,
        "get_dynamodb_metrics": get_dynamodb_metrics,
        "query_cloudwatch_logs": query_cloudwatch_logs,
        "get_infra_metrics": get_infra_metrics,
        "get_cloudwatch_alarms": get_cloudwatch_alarms,
        "plan_instance_refresh": plan_instance_refresh,
        "execute_instance_refresh": execute_instance_refresh,
        "check_api_health": check_api_health,
        "check_api_pagination": check_api_pagination,
        "get_baseline_check_all": get_baseline_check_all,  # Composite baseline check
        "get_latest_http_5xx": get_latest_http_5xx,  # Latest 5xx finder (basic)
        "get_5xx_root_cause_analysis": get_5xx_root_cause_analysis,  # NEW: Smart RCA for 5xx
    }

    # If invoked via API schema, map apiPath -> function name
    if not function_name and api_path:
        function_name = api_path.lstrip("/")

    # Normalize some parameters from OpenAPI (strings) into expected Python types
    if function_name == "get_dynamodb_metrics":
        table_names = params.get("table_names")
        if isinstance(table_names, str):
            params["table_names"] = [t.strip() for t in table_names.split(",") if t.strip()]
    if function_name == "query_cloudwatch_logs":
        lgn = params.get("log_group_names")
        if isinstance(lgn, str):
            sentinel = lgn.strip().upper()
            # Some models may incorrectly pass the env var name instead of omitting the parameter.
            if sentinel in {"OPS_LOG_GROUPS", "DEFAULT"}:
                params.pop("log_group_names", None)
            else:
                params["log_group_names"] = [g.strip() for g in lgn.split(",") if g.strip()]
    if function_name == "check_api_health":
        endpoints = params.get("endpoints")
        if isinstance(endpoints, str):
            params["endpoints"] = [e.strip() for e in endpoints.split(",") if e.strip()]
    
    http_status = 200
    if function_name in action_functions:
        try:
            result = action_functions[function_name](**params)
            response_json = json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            http_status = 500
            response_json = json.dumps({"error": str(e)}, ensure_ascii=False)
    else:
        http_status = 400
        response_json = json.dumps(
            {
                "error": f"Unknown function: {function_name}",
                "available_functions": list(action_functions.keys()),
            },
            ensure_ascii=False,
        )

    # Build Bedrock response body:
    # - API schema mode expects a content-type key like application/json
    # - Function-details mode may accept TEXT
    if api_path or http_method:
        response_body = {
            "application/json": {
                "body": response_json
            }
        }
    else:
        response_body = {
            "TEXT": {
                "body": response_json
            }
        }
    
    # Return response in Bedrock Agent format
    # Build final response in the correct Bedrock format.
    # - API schema mode: response.responseBody + httpStatusCode
    # - Function details mode: response.functionResponse.responseBody
    if api_path or http_method or event.get("apiPath") or event.get("verb"):
        response: Dict[str, Any] = {
            "actionGroup": action_group,
            "apiPath": api_path,
            "httpMethod": http_method or (str(event.get("verb") or "GET").upper()),
            "httpStatusCode": http_status,
            "responseBody": response_body,
        }
    else:
        response = {
            "actionGroup": action_group,
            "function": function_name,
            "functionResponse": {
                "responseBody": response_body
            },
        }

    return {
        "messageVersion": "1.0",
        "response": response,
    }
