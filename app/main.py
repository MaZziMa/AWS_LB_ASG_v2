"""
Course Management System - Main Application
FastAPI application with DynamoDB integration
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file before other imports

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import boto3
from boto3.dynamodb.conditions import Attr, Key
import base64
from decimal import Decimal
import json
import os
import logging
import socket
import time
import traceback
import uuid
import urllib.error
import urllib.request
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime
from time import perf_counter
from fastapi import APIRouter
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
    EndpointConnectionError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat()


def _instance_id() -> str:
    return socket.gethostname()


def _log_json(level: int, payload: Dict[str, Any]) -> None:
    """Emit a single-line JSON log record.

    CloudWatch Logs Insights can extract JSON keys from @message for queries.
    """
    try:
        logger.log(level, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    except Exception:
        # Never let logging break request handling
        logger.log(level, str(payload))


def _app_version() -> str:
    return os.getenv("APP_VERSION", "1.0.0")


def _build_info() -> Dict[str, Any]:
    return {
        "app_name": os.getenv("APP_NAME", "Course Management System"),
        "app_version": _app_version(),
        "git_sha": os.getenv("GIT_SHA") or os.getenv("SOURCE_VERSION"),
        "build_time": os.getenv("BUILD_TIME"),
        "ami_id": os.getenv("AMI_ID"),
        "ami_name": os.getenv("AMI_NAME"),
        "instance_id": _instance_id(),
        "timestamp": _now_utc_iso(),
    }


def _imds_token(timeout_seconds: float = 0.2) -> Optional[str]:
    """Best-effort IMDSv2 token fetch; returns None if unavailable."""

    try:
        req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            token = resp.read().decode("utf-8", errors="ignore").strip()
            return token or None
    except Exception:
        return None


def _imds_get(path: str, timeout_seconds: float = 0.2) -> Optional[str]:
    """Best-effort read from EC2 Instance Metadata Service (IMDS)."""

    url = f"http://169.254.169.254{path}"
    token = _imds_token(timeout_seconds=timeout_seconds)
    headers: Dict[str, str] = {}
    if token:
        headers["X-aws-ec2-metadata-token"] = token
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return resp.read().decode("utf-8", errors="ignore").strip() or None
    except Exception:
        return None


def _ec2_instance_identity(timeout_seconds: float = 0.25) -> Optional[Dict[str, Any]]:
    raw = _imds_get("/latest/dynamic/instance-identity/document", timeout_seconds=timeout_seconds)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _describe_ami(ami_id: str, region_name: str) -> Optional[Dict[str, Any]]:
    """Best-effort DescribeImages for the AMI in use.

    Requires instance role permission: ec2:DescribeImages (and optionally DescribeImageAttribute).
    """

    try:
        ec2 = boto3.client("ec2", region_name=region_name)
        resp = ec2.describe_images(ImageIds=[ami_id])
        images = resp.get("Images") or []
        if not images:
            return None
        img = images[0]

        tags = {t.get("Key"): t.get("Value") for t in (img.get("Tags") or []) if t.get("Key")}
        visibility = "Public" if img.get("Public") else "Private"
        source_ami_id = tags.get("SourceAmiId") or tags.get("source_ami_id")
        source_ami_region = tags.get("SourceAmiRegion") or tags.get("source_ami_region")

        deregistration_protection = None
        try:
            attr = ec2.describe_image_attribute(ImageId=ami_id, Attribute="deregistrationProtection")
            deregistration_protection = (
                attr.get("DeregistrationProtection", {}) or {}
            ).get("Value")
        except Exception:
            deregistration_protection = None

        block_devices = []
        for bdm in img.get("BlockDeviceMappings") or []:
            ebs = bdm.get("Ebs") or {}
            block_devices.append(
                {
                    "device_name": bdm.get("DeviceName"),
                    "snapshot_id": ebs.get("SnapshotId"),
                    "volume_size": ebs.get("VolumeSize"),
                    "delete_on_termination": ebs.get("DeleteOnTermination"),
                    "encrypted": ebs.get("Encrypted"),
                }
            )

        return {
            "name": img.get("Name"),
            "ami_name": img.get("Name"),
            "ami_id": img.get("ImageId"),
            "source": img.get("ImageLocation") or (f"{img.get('OwnerId')}/{img.get('Name')}"),
            "owner": img.get("OwnerId"),
            "visibility": visibility,
            "status": img.get("State"),
            "creation_date": img.get("CreationDate"),
            "platform": img.get("Platform"),
            "platform_details": img.get("PlatformDetails"),
            "root_device_type": img.get("RootDeviceType"),
            "block_devices": block_devices,
            "virtualization": img.get("VirtualizationType"),
            "deprecation_time": img.get("DeprecationTime"),
            "last_launched_time": img.get("LastLaunchedTime"),
            "deregistration_protection": deregistration_protection,
            "source_ami_id": source_ami_id,
            "source_ami_region": source_ami_region,
        }
    except (NoCredentialsError, PartialCredentialsError):
        return None
    except ClientError:
        return None
    except Exception:
        return None

# Initialize FastAPI app
app = FastAPI(
    title="Course Management System",
    description="Learning platform with AWS Load Balancer and Auto Scaling",
    version="1.0.0",
)


@app.middleware("http")
async def structured_access_log(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    start = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        latency_ms = round((perf_counter() - start) * 1000, 2)
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        _log_json(
            logging.INFO,
            {
                "log_type": "http_access",
                "timestamp": _now_utc_iso(),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": request.url.query,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "instance_id": _instance_id(),
            },
        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    _log_json(
        logging.ERROR,
        {
            "log_type": "exception",
            "timestamp": _now_utc_iso(),
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "instance_id": _instance_id(),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "stacktrace": traceback.format_exc(),
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "request_id": request_id},
    )

# Bedrock Agent integration
try:
    from app.bedrock_kb import invoke_customer_agent, invoke_ops_agent
    from app.ops_realtime import (
        collect_infra_snapshot,
        collect_infra_snapshot_cached,
        default_alb_arn,
        default_asg_name,
        default_region,
        default_target_group_arn,
        collect_dynamodb_metrics,
        execute_asg_instance_refresh,
        execute_ddb_capacity_increase,
        persist_snapshot_to_logs,
        plan_asg_instance_refresh,
        plan_ddb_capacity_increase,
        resolve_infra_identifiers,
        sse_infra_stream,
    )

    # Pydantic model for Agent query
    class AgentQuery(BaseModel):
        question: str
        session_id: Optional[str] = None  # For multi-turn conversations

    @app.post("/api/customer/ask")
    async def ask_customer_agent(query: AgentQuery):
        """Query customer support agent (courses, enrollment, billing, campus info)"""
        try:
            result = invoke_customer_agent(query.question, query.session_id)
            return result
        except Exception as e:
            logger.error(f"Customer Agent error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/ops/ask")
    async def ask_ops_agent(query: AgentQuery):
        """Query ops agent (ALB, ASG, deployments, incident response)"""
        try:
            result = invoke_ops_agent(query.question, query.session_id)
            return result
        except Exception as e:
            logger.error(f"Ops Agent error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/ops/realtime")
    async def ops_realtime(
        minutes: int = 5,
        log_group: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Summarize recent logs (last N minutes) using CloudWatch Logs Insights.

        This endpoint is intended to be called by an ops agent/tooling to answer
        questions like: "What endpoints are erroring right now?".

        Requires IAM permissions on the instance role:
          logs:StartQuery, logs:GetQueryResults, logs:StopQuery
        """

        minutes = max(1, min(minutes, 60))
        region_name = region or os.getenv("AWS_REGION", "us-east-1")
        group = (
            log_group
            or os.getenv("CLOUDWATCH_LOG_GROUP")
            or os.getenv("CW_LOG_GROUP")
        )
        if not group:
            raise HTTPException(
                status_code=400,
                detail="Missing log group. Provide ?log_group=... or set CLOUDWATCH_LOG_GROUP.",
            )

        logs = boto3.client("logs", region_name=region_name)
        end_time = int(time.time())
        start_time = end_time - (minutes * 60)

        def run_query(query_string: str, timeout_seconds: int = 12) -> List[Dict[str, Any]]:
            try:
                resp = logs.start_query(
                    logGroupName=group,
                    startTime=start_time,
                    endTime=end_time,
                    queryString=query_string,
                    limit=200,
                )
            except logs.exceptions.ResourceNotFoundException:
                raise HTTPException(status_code=404, detail=f"CloudWatch log group not found: {group}")
            except (NoCredentialsError, PartialCredentialsError):
                raise HTTPException(
                    status_code=403,
                    detail="CloudWatch Logs credentials error: no/partial AWS credentials configured",
                )
            except EndpointConnectionError as e:
                raise HTTPException(status_code=503, detail=f"CloudWatch Logs endpoint connection error: {e}")
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code")
                if code in {"AccessDeniedException", "UnrecognizedClientException"}:
                    raise HTTPException(status_code=403, detail=f"CloudWatch Logs permission/credentials error: {code}")
                raise
            query_id = resp["queryId"]
            deadline = time.time() + timeout_seconds
            while True:
                try:
                    result = logs.get_query_results(queryId=query_id)
                except (NoCredentialsError, PartialCredentialsError):
                    raise HTTPException(
                        status_code=403,
                        detail="CloudWatch Logs credentials error: no/partial AWS credentials configured",
                    )
                except EndpointConnectionError as e:
                    raise HTTPException(status_code=503, detail=f"CloudWatch Logs endpoint connection error: {e}")
                except ClientError as e:
                    code = e.response.get("Error", {}).get("Code")
                    if code in {"AccessDeniedException", "UnrecognizedClientException"}:
                        raise HTTPException(status_code=403, detail=f"CloudWatch Logs permission/credentials error: {code}")
                    raise
                status = result.get("status")
                if status == "Complete":
                    rows = []
                    for row in result.get("results", []):
                        item: Dict[str, Any] = {}
                        for cell in row:
                            item[cell.get("field")] = cell.get("value")
                        rows.append(item)
                    return rows
                if status in {"Failed", "Cancelled", "Timeout"}:
                    return []
                if time.time() > deadline:
                    try:
                        logs.stop_query(queryId=query_id)
                    except Exception:
                        pass
                    return []
                time.sleep(0.8)

        q_top_5xx_paths = (
            "fields log_type, path, status_code, latency_ms "
            "| filter log_type = \"http_access\" and status_code >= 500 "
            "| stats count() as errors, pct(latency_ms, 95) as p95_latency_ms by path "
            "| sort errors desc "
            "| limit 20"
        )
        q_top_5xx_instances = (
            "fields log_type, instance_id, status_code "
            "| filter log_type = \"http_access\" and status_code >= 500 "
            "| stats count() as errors by instance_id "
            "| sort errors desc "
            "| limit 10"
        )
        q_top_errors = (
            "fields log_type, error_type "
            "| filter log_type = \"exception\" "
            "| stats count() as errors by error_type "
            "| sort errors desc "
            "| limit 10"
        )
        q_recent_exceptions = (
            "fields @timestamp, request_id, method, path, instance_id, error_type, error_message "
            "| filter log_type = \"exception\" "
            "| sort @timestamp desc "
            "| limit 20"
        )

        return {
            "log_group": group,
            "region": region_name,
            "window_minutes": minutes,
            "window_start": datetime.utcfromtimestamp(start_time).isoformat(),
            "window_end": datetime.utcfromtimestamp(end_time).isoformat(),
            "top_5xx_paths": run_query(q_top_5xx_paths),
            "top_5xx_instances": run_query(q_top_5xx_instances),
            "top_error_types": run_query(q_top_errors),
            "recent_exceptions": run_query(q_recent_exceptions),
        }

    @app.post("/api/ops/realtime/infra/snapshot")
    async def ops_snapshot_log(
        asg_name: Optional[str] = None,
        target_group_arn: Optional[str] = None,
        alb_arn: Optional[str] = None,
        region: Optional[str] = None,
        log: bool = True,
    ):
        """Collect an infra snapshot and optionally persist to CloudWatch Logs."""

        region_name = region or default_region()
        resolved = resolve_infra_identifiers(
            region=region_name,
            asg_name=asg_name,
            target_group_arn=target_group_arn,
            alb_arn=alb_arn,
        )
        snap = collect_infra_snapshot_cached(
            region=region_name,
            asg_name=resolved.get("asg_name"),
            target_group_arn=resolved.get("target_group_arn"),
            alb_arn=resolved.get("alb_arn"),
        )
        snap["discovery"] = resolved.get("discovery")
        log_status: Dict[str, Any] = {"ok": False, "skipped": not log}
        if log:
            log_status = persist_snapshot_to_logs(region=region_name, snapshot=snap)
        return {"snapshot": snap, "log_status": log_status}

    @app.get("/api/ops/dynamodb/metrics")
    async def ops_dynamodb_metrics(
        tables: Optional[str] = None,
        minutes: int = 5,
        region: Optional[str] = None,
    ):
        """Lightweight DynamoDB metrics snapshot (throttle/consumed/provisioned)."""

        region_name = region or default_region()
        table_list: List[str] = []
        if tables:
            table_list.extend([t.strip() for t in tables.split(",") if t.strip()])
        env_tables = [
            os.getenv("COURSES_TABLE"),
            os.getenv("STUDENTS_TABLE"),
            os.getenv("ENROLLMENTS_TABLE"),
        ]
        for t in env_tables:
            if t and t not in table_list:
                table_list.append(t)
        if not table_list:
            raise HTTPException(status_code=400, detail="No DynamoDB tables provided")
        return collect_dynamodb_metrics(region=region_name, table_names=table_list, minutes=minutes)

    @app.post("/api/ops/actions/asg/instance-refresh")
    async def ops_action_instance_refresh(
        asg_name: Optional[str] = None,
        region: Optional[str] = None,
        approve: bool = False,
    ):
        """Plan or execute a Rolling instance refresh (requires approve=true to execute)."""

        region_name = region or default_region()
        target_asg = asg_name or default_asg_name()
        if not target_asg:
            raise HTTPException(status_code=400, detail="Missing asg_name")
        if not approve:
            return {"approval_required": True, **plan_asg_instance_refresh(region=region_name, asg_name=target_asg)}
        return execute_asg_instance_refresh(region=region_name, asg_name=target_asg)

    @app.post("/api/ops/actions/dynamodb/capacity")
    async def ops_action_ddb_capacity(
        table_name: Optional[str] = None,
        region: Optional[str] = None,
        factor: float = 1.5,
        max_increment: int = 100,
        approve: bool = False,
    ):
        """Plan or execute a bounded RCU/WCU increase for provisioned tables."""

        region_name = region or default_region()
        if not table_name:
            raise HTTPException(status_code=400, detail="Missing table_name")
        if not approve:
            return {
                "approval_required": True,
                **plan_ddb_capacity_increase(
                    region=region_name,
                    table_name=table_name,
                    factor=factor,
                    max_increment=max_increment,
                ),
            }
        return execute_ddb_capacity_increase(
            region=region_name,
            table_name=table_name,
            factor=factor,
            max_increment=max_increment,
        )

    @app.get("/api/ops/realtime/infra")
    async def ops_realtime_infra(
        asg_name: Optional[str] = None,
        target_group_arn: Optional[str] = None,
        alb_arn: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Best-effort snapshot of ASG/ALB/TG state for ops diagnostics."""

        region_name = region or default_region()
        resolved = resolve_infra_identifiers(
            region=region_name,
            asg_name=asg_name,
            target_group_arn=target_group_arn,
            alb_arn=alb_arn,
        )
        snap = collect_infra_snapshot_cached(
            region=region_name,
            asg_name=resolved.get("asg_name"),
            target_group_arn=resolved.get("target_group_arn"),
            alb_arn=resolved.get("alb_arn"),
        )
        snap["discovery"] = resolved.get("discovery")
        return snap

    @app.get("/api/ops/realtime/infra/stream")
    async def ops_realtime_infra_stream(
        asg_name: Optional[str] = None,
        target_group_arn: Optional[str] = None,
        alb_arn: Optional[str] = None,
        region: Optional[str] = None,
        interval_seconds: int = 5,
        max_events: int = 120,
    ):
        """Server-Sent Events stream of infra snapshots (works fine behind ALB)."""

        region_name = region or default_region()
        resolved = resolve_infra_identifiers(
            region=region_name,
            asg_name=asg_name,
            target_group_arn=target_group_arn,
            alb_arn=alb_arn,
        )
        gen = sse_infra_stream(
            region=region_name,
            asg_name=resolved.get("asg_name"),
            target_group_arn=resolved.get("target_group_arn"),
            alb_arn=resolved.get("alb_arn"),
            interval_seconds=interval_seconds,
            max_events=max_events,
        )
        return StreamingResponse(gen, media_type="text/event-stream")

    logger.info("Bedrock Agents enabled: customer (LJCIO6MTHB), ops (CGWF5H93V2)")
except Exception as e:
    logger.warning(f"Bedrock Agents not available: {str(e)}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DynamoDB setup
dynamodb: Any = boto3.resource(
    "dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1")
)
COURSES_TABLE = os.getenv("COURSES_TABLE", "courses")
STUDENTS_TABLE = os.getenv("STUDENTS_TABLE", "students")
ENROLLMENTS_TABLE = os.getenv("ENROLLMENTS_TABLE", "enrollments")

ENABLE_DYNAMODB = os.getenv("ENABLE_DYNAMODB", "true").strip().lower() == "true"


# Pydantic models
class Course(BaseModel):
    course_id: str
    title: str
    description: str
    instructor: str
    duration_hours: int
    price: float
    category: str


class Student(BaseModel):
    student_id: str
    name: str
    email: str
    phone: Optional[str] = None


class Enrollment(BaseModel):
    enrollment_id: str
    student_id: str
    course_id: str
    enrolled_date: str
    progress: int = 0
    completed: bool = False


# Helper function to convert Decimal to float
def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def _normalize_dynamodb_item(item: dict) -> dict:
    def normalize_value(value: Any):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, dict):
            return {k: normalize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize_value(v) for v in value]
        return value

    return {k: normalize_value(v) for k, v in item.items()}


def _encode_cursor(last_evaluated_key: Optional[dict]) -> Optional[str]:
    if not last_evaluated_key:
        return None
    raw = json.dumps(last_evaluated_key, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: Optional[str]) -> Optional[dict]:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        decoded = json.loads(raw)
        return decoded if isinstance(decoded, dict) else None
    except Exception:
        return None


# Health check endpoint for Load Balancer
@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint for ALB target group"""
    hostname = socket.gethostname()
    client_ip = request.client.host if request.client else "unknown"
    _log_json(
        logging.INFO,
        {
            "log_type": "health",
            "timestamp": _now_utc_iso(),
            "instance_id": hostname,
            "client_ip": client_ip,
        },
    )
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "course-management-system",
        "instance_id": hostname,
        "client_ip": client_ip,
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Course Management System API",
        "version": _app_version(),
        "endpoints": {
            "courses": "/courses",
            "students": "/students",
            "enrollments": "/enrollments",
            "health": "/health",
            "cpu_burn": "/cpu-burn",
        },
    }


@app.get("/version")
async def version():
    """Lightweight deploy/version info endpoint.

    Intended for quickly verifying which build is running behind an ALB/ASG.
    Values are populated from environment variables when available.
    """

    info = _build_info()

    identity = _ec2_instance_identity()
    if identity:
        info["ec2_identity"] = {
            "account_id": identity.get("accountId"),
            "region": identity.get("region"),
            "availability_zone": identity.get("availabilityZone"),
            "instance_id": identity.get("instanceId"),
            "image_id": identity.get("imageId"),
            "instance_type": identity.get("instanceType"),
            "architecture": identity.get("architecture"),
            "private_ip": identity.get("privateIp"),
        }

        # Prefer identity-provided values when env isn't set
        if not info.get("ami_id"):
            info["ami_id"] = identity.get("imageId")
        if not info.get("instance_id"):
            info["instance_id"] = identity.get("instanceId")
        region_val = identity.get("region")
        if not os.getenv("AWS_REGION") and region_val:
            os.environ["AWS_REGION"] = str(region_val)

    region_name = os.getenv("AWS_REGION", "us-east-1")
    ami_id = info.get("ami_id")
    if ami_id:
        ami_details = _describe_ami(ami_id=ami_id, region_name=region_name)
        if ami_details:
            info["ami"] = ami_details
            # Backfill top-level ami_name when available
            if not info.get("ami_name"):
                info["ami_name"] = ami_details.get("ami_name")

    return info


# ============ COURSES ENDPOINTS ============
@app.get("/courses")
async def get_courses(
    q: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
):
    """Get courses with optional search + pagination.

    Query params:
    - q: free-text search (title/description/instructor/course_id/category)
    - category: exact category filter (uses GSI CategoryIndex if available)
    - limit: page size (1..100)
    - cursor: continuation token returned by previous call
    """
    try:
        limit = max(1, min(limit, 100))
        table = dynamodb.Table(COURSES_TABLE)

        exclusive_start_key = _decode_cursor(cursor)

        search_filter = None
        if q:
            q_stripped = q.strip()
            if q_stripped:
                search_filter = (
                    Attr("title").contains(q_stripped)
                    | Attr("description").contains(q_stripped)
                    | Attr("instructor").contains(q_stripped)
                    | Attr("course_id").contains(q_stripped)
                    | Attr("category").contains(q_stripped)
                )

        # Prefer GSI query when category is specified (more efficient on AWS)
        response = None
        if category:
            try:
                query_kwargs: dict = {
                    "IndexName": "CategoryIndex",
                    "KeyConditionExpression": Key("category").eq(category),
                    "Limit": limit,
                }
                if search_filter is not None:
                    query_kwargs["FilterExpression"] = search_filter
                if exclusive_start_key is not None:
                    query_kwargs["ExclusiveStartKey"] = exclusive_start_key
                response = table.query(**query_kwargs)
            except Exception:
                # Fallback to scan if local table/GSI isn't available
                response = None

        if response is None:
            scan_kwargs: dict = {"Limit": limit}
            combined_filter = None
            if category:
                combined_filter = Attr("category").eq(category)
            if search_filter is not None:
                combined_filter = (
                    search_filter
                    if combined_filter is None
                    else (combined_filter & search_filter)
                )
            if combined_filter is not None:
                scan_kwargs["FilterExpression"] = combined_filter
            if exclusive_start_key is not None:
                scan_kwargs["ExclusiveStartKey"] = exclusive_start_key
            response = table.scan(**scan_kwargs)

        courses = response.get("Items", [])
        courses = [_normalize_dynamodb_item(c) for c in courses]

        last_evaluated_key = response.get("LastEvaluatedKey")
        next_cursor = _encode_cursor(last_evaluated_key)

        return {
            "courses": courses,
            "count": len(courses),
            "limit": limit,
            "next_cursor": next_cursor,
        }
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/courses/{course_id}")
async def get_course(course_id: str):
    """Get a specific course by ID"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(COURSES_TABLE)
        response = table.get_item(Key={"course_id": course_id})

        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Course not found")

        course = response["Item"]
        for key, value in course.items():
            if isinstance(value, Decimal):
                course[key] = float(value)

        return course
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/courses")
async def create_course(course: Course):
    """Create a new course"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(COURSES_TABLE)
        item = course.dict()
        item["created_at"] = datetime.utcnow().isoformat()
        # DynamoDB does not allow native Python float, convert to Decimal
        if isinstance(item.get("price"), float):
            # Use str() to avoid floating point representation issues
            item["price"] = Decimal(str(item["price"]))

        table.put_item(Item=item)
        # Convert back for response consistency
        response_course = course.dict()
        return {"message": "Course created successfully", "course": response_course}
    except Exception as e:
        logger.error(f"Error creating course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/courses/{course_id}")
async def delete_course(course_id: str):
    """Delete a course"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(COURSES_TABLE)
        table.delete_item(Key={"course_id": course_id})
        return {"message": "Course deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ STUDENTS ENDPOINTS ============
@app.get("/students")
async def get_students():
    """Get all students"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        response = table.scan()
        students = response.get("Items", [])
        return {"students": students, "count": len(students)}
    except Exception as e:
        logger.error(f"Error fetching students: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/students/{student_id}")
async def get_student(student_id: str):
    """Get a specific student by ID"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        response = table.get_item(Key={"student_id": student_id})

        if "Item" not in response:
            raise HTTPException(status_code=404, detail="Student not found")

        return response["Item"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/students")
async def create_student(student: Student):
    """Create a new student"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(STUDENTS_TABLE)
        item = student.dict()
        item["created_at"] = datetime.utcnow().isoformat()

        table.put_item(Item=item)
        return {"message": "Student created successfully", "student": student}
    except Exception as e:
        logger.error(f"Error creating student: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ ENROLLMENTS ENDPOINTS ============
@app.get("/enrollments")
async def get_enrollments():
    """Get all enrollments"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        response = table.scan()
        enrollments = response.get("Items", [])

        # Convert Decimal to float
        for enrollment in enrollments:
            for key, value in enrollment.items():
                if isinstance(value, Decimal):
                    enrollment[key] = float(value)

        return {"enrollments": enrollments, "count": len(enrollments)}
    except Exception as e:
        logger.error(f"Error fetching enrollments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enrollments")
async def create_enrollment(enrollment: Enrollment):
    """Create a new enrollment"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        item = enrollment.dict()
        item["created_at"] = datetime.utcnow().isoformat()

        table.put_item(Item=item)
        return {"message": "Enrollment created successfully", "enrollment": enrollment}
    except Exception as e:
        logger.error(f"Error creating enrollment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/enrollments/student/{student_id}")
async def get_student_enrollments(student_id: str):
    """Get all enrollments for a specific student"""
    if not ENABLE_DYNAMODB:
        raise HTTPException(status_code=501, detail="DynamoDB endpoints disabled. Set ENABLE_DYNAMODB=true to enable.")
    
    try:
        table = dynamodb.Table(ENROLLMENTS_TABLE)
        response = table.scan(
            FilterExpression="student_id = :sid",
            ExpressionAttributeValues={":sid": student_id},
        )
        enrollments = response.get("Items", [])

        # Convert Decimal to float
        for enrollment in enrollments:
            for key, value in enrollment.items():
                if isinstance(value, Decimal):
                    enrollment[key] = float(value)

        return {"enrollments": enrollments, "count": len(enrollments)}
    except Exception as e:
        logger.error(f"Error fetching student enrollments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cpu-burn")
async def cpu_burn(iterations: int = 50_000_000):
    """Artificially burn CPU cycles to test auto-scaling behavior."""
    try:
        # Bound iterations to avoid accidentally freezing the instance
        bounded_iterations = max(1, min(iterations, 200_000_000))
        start = perf_counter()
        accumulator = 0
        for i in range(bounded_iterations):
            accumulator += (i % 5) * (i % 3)
        duration = perf_counter() - start
        return {
            "requested_iterations": iterations,
            "executed_iterations": bounded_iterations,
            "result": accumulator,
            "duration_seconds": round(duration, 3),
        }
    except Exception as e:
        logger.error(f"Error during cpu-burn: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/raise-500")
async def debug_raise_500(mode: str = "exception"):
    """Temporary debug endpoint to force a 500 response for testing AIOps.

    - Call `/debug/raise-500` to raise an unhandled exception (returns 500).
    - Optionally pass `?mode=message` to return a harmless payload instead.
    Remove this endpoint after testing.
    """
    if mode == "message":
        return {"message": "debug endpoint active"}
    # Raise an exception so the global exception handler logs a 500 and request_id
    raise RuntimeError("Intentional test 500 triggered via /debug/raise-500")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
