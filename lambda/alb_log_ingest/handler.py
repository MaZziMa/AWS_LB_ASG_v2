"""
ALB Access Logs Ingest Lambda

This Lambda is triggered by S3 when new ALB access log files (.log.gz) are uploaded.
It reads the gzip file, parses ALB log format, and writes to CloudWatch Logs
in a structured JSON format that AIOps can query.

ALB Log Format (space-separated, some fields can be "-"):
type timestamp elb client:port target:port request_processing_time 
target_processing_time response_processing_time elb_status_code 
target_status_code received_bytes sent_bytes "request" "user_agent" 
ssl_cipher ssl_protocol target_group_arn "trace_id" "domain_name" 
"chosen_cert_arn" matched_rule_priority request_creation_time 
"actions_executed" "redirect_url" "error_reason" 
"target:port_list" "target_status_code_list" "classification" 
"classification_reason"
"""
import gzip
import json
import os
import re
import urllib.parse
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import boto3

# Configuration
LOG_GROUP_NAME = os.getenv("LOG_GROUP_NAME", "/aws/alb/course-management-dev")
REGION = os.getenv("REGION", "us-east-1")

# AWS Clients
s3_client = boto3.client("s3", region_name=REGION)
logs_client = boto3.client("logs", region_name=REGION)

# ALB log field indices (0-based)
ALB_FIELDS = {
    "type": 0,
    "timestamp": 1,
    "elb": 2,
    "client_port": 3,
    "target_port": 4,
    "request_processing_time": 5,
    "target_processing_time": 6,
    "response_processing_time": 7,
    "elb_status_code": 8,
    "target_status_code": 9,
    "received_bytes": 10,
    "sent_bytes": 11,
    "request": 12,
    "user_agent": 13,
    "ssl_cipher": 14,
    "ssl_protocol": 15,
    "target_group_arn": 16,
    "trace_id": 17,
    "domain_name": 18,
    "chosen_cert_arn": 19,
    "matched_rule_priority": 20,
    "request_creation_time": 21,
    "actions_executed": 22,
    "redirect_url": 23,
    "error_reason": 24,
}


def parse_alb_log_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single ALB access log line.
    
    ALB logs are space-separated but quoted fields can contain spaces.
    Returns structured dict or None if parsing fails.
    """
    if not line or line.startswith("#"):
        return None
    
    # Parse quoted and unquoted fields
    # Pattern: either "quoted string" or non-space characters
    pattern = r'"([^"]*)"|\S+'
    matches = re.findall(pattern, line)
    
    # findall returns tuple for groups; flatten
    fields = []
    for match in re.finditer(pattern, line):
        if match.group(1) is not None:  # Quoted string
            fields.append(match.group(1))
        else:
            fields.append(match.group(0))
    
    if len(fields) < 13:
        return None
    
    try:
        # Parse timestamp
        timestamp_str = fields[ALB_FIELDS["timestamp"]]
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            timestamp_epoch_ms = int(dt.timestamp() * 1000)
        except Exception:
            timestamp_epoch_ms = int(datetime.utcnow().timestamp() * 1000)
        
        # Parse request line: "GET /path HTTP/1.1"
        request_line = fields[ALB_FIELDS["request"]] if len(fields) > ALB_FIELDS["request"] else "-"
        method, path, protocol = "-", "-", "-"
        if request_line and request_line != "-":
            request_parts = request_line.split(" ", 2)
            if len(request_parts) >= 2:
                method = request_parts[0]
                path = request_parts[1]
                if len(request_parts) >= 3:
                    protocol = request_parts[2]
        
        # Parse client IP:port
        client_port = fields[ALB_FIELDS["client_port"]]
        client_ip = client_port.split(":")[0] if ":" in client_port else client_port
        
        # Parse target IP:port
        target_port = fields[ALB_FIELDS["target_port"]]
        target_ip = target_port.split(":")[0] if ":" in target_port else target_port
        
        # Parse status codes
        elb_status = _safe_int(fields[ALB_FIELDS["elb_status_code"]])
        target_status = _safe_int(fields[ALB_FIELDS["target_status_code"]])
        
        # Parse processing times (seconds -> milliseconds)
        request_time = _safe_float(fields[ALB_FIELDS["request_processing_time"]])
        target_time = _safe_float(fields[ALB_FIELDS["target_processing_time"]])
        response_time = _safe_float(fields[ALB_FIELDS["response_processing_time"]])
        
        # Total latency in ms
        total_latency_ms = None
        if request_time is not None and target_time is not None and response_time is not None:
            total_latency_ms = round((request_time + target_time + response_time) * 1000, 2)
        
        # Parse user agent
        user_agent = fields[ALB_FIELDS["user_agent"]] if len(fields) > ALB_FIELDS["user_agent"] else "-"
        
        # Parse trace ID (for X-Ray correlation)
        trace_id = fields[ALB_FIELDS["trace_id"]] if len(fields) > ALB_FIELDS["trace_id"] else "-"
        
        # Parse error reason (important for 5xx debugging)
        error_reason = fields[ALB_FIELDS["error_reason"]] if len(fields) > ALB_FIELDS["error_reason"] else "-"
        
        # Determine effective status code (use ELB status, which includes ALB-generated errors)
        status_code = elb_status if elb_status else target_status
        
        return {
            "timestamp": timestamp_str,
            "timestamp_epoch_ms": timestamp_epoch_ms,
            "log_type": "alb_access",
            "status_code": status_code,
            "elb_status_code": elb_status,
            "target_status_code": target_status,
            "method": method,
            "path": path,
            "protocol": protocol,
            "client_ip": client_ip,
            "target_ip": target_ip,
            "latency_ms": total_latency_ms,
            "request_processing_time_ms": round(request_time * 1000, 2) if request_time else None,
            "target_processing_time_ms": round(target_time * 1000, 2) if target_time else None,
            "response_processing_time_ms": round(response_time * 1000, 2) if response_time else None,
            "received_bytes": _safe_int(fields[ALB_FIELDS["received_bytes"]]),
            "sent_bytes": _safe_int(fields[ALB_FIELDS["sent_bytes"]]),
            "user_agent": user_agent if user_agent != "-" else None,
            "trace_id": trace_id if trace_id != "-" else None,
            "error_reason": error_reason if error_reason != "-" else None,
            "elb_name": fields[ALB_FIELDS["elb"]],
        }
    
    except Exception as e:
        print(f"Error parsing line: {e}")
        return None


def _safe_int(val: str) -> Optional[int]:
    """Safely convert to int, return None for '-' or invalid."""
    if val == "-" or not val:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val: str) -> Optional[float]:
    """Safely convert to float, return None for '-' or invalid."""
    if val == "-" or not val:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def get_or_create_log_stream(log_group: str, log_stream: str) -> None:
    """Create log stream if it doesn't exist."""
    try:
        logs_client.create_log_stream(
            logGroupName=log_group,
            logStreamName=log_stream
        )
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass


def put_log_events(log_group: str, log_stream: str, events: List[Dict]) -> None:
    """Put log events to CloudWatch Logs with retry logic."""
    if not events:
        return
    
    # Sort by timestamp (required by CloudWatch)
    events.sort(key=lambda x: x["timestamp"])
    
    # Get sequence token if stream exists
    try:
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=log_stream,
            limit=1
        )
        
        sequence_token = None
        if response.get("logStreams"):
            sequence_token = response["logStreams"][0].get("uploadSequenceToken")
        
        kwargs = {
            "logGroupName": log_group,
            "logStreamName": log_stream,
            "logEvents": events,
        }
        if sequence_token:
            kwargs["sequenceToken"] = sequence_token
        
        logs_client.put_log_events(**kwargs)
        
    except logs_client.exceptions.InvalidSequenceTokenException as e:
        # Retry with correct token
        token = str(e).split("sequenceToken is: ")[-1].strip()
        logs_client.put_log_events(
            logGroupName=log_group,
            logStreamName=log_stream,
            logEvents=events,
            sequenceToken=token
        )


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for S3 event.
    
    Triggered when new ALB log file is uploaded to S3.
    Reads gzip file, parses logs, writes to CloudWatch Logs.
    """
    print(f"Received event: {json.dumps(event)}")
    
    processed_count = 0
    error_count = 0
    skipped_count = 0
    
    for record in event.get("Records", []):
        try:
            # Get S3 object info
            bucket = record["s3"]["bucket"]["name"]
            key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
            
            print(f"Processing s3://{bucket}/{key}")
            
            # Download and decompress
            response = s3_client.get_object(Bucket=bucket, Key=key)
            compressed_data = response["Body"].read()
            
            with gzip.GzipFile(fileobj=BytesIO(compressed_data)) as gz:
                content = gz.read().decode("utf-8")
            
            # Parse each line
            lines = content.strip().split("\n")
            log_events = []
            
            # Create log stream name from S3 key (e.g., alb-logs/AWSLogs/.../20251225...)
            # Extract date part for log stream name
            log_stream = key.replace("/", "-").replace(".log.gz", "")
            
            for line in lines:
                parsed = parse_alb_log_line(line)
                if parsed:
                    # Check if it's an error (4xx or 5xx) - log all, but prioritize errors
                    status = parsed.get("status_code")
                    
                    log_events.append({
                        "timestamp": parsed["timestamp_epoch_ms"],
                        "message": json.dumps(parsed, ensure_ascii=False)
                    })
                    processed_count += 1
                else:
                    skipped_count += 1
            
            # Write to CloudWatch Logs
            if log_events:
                get_or_create_log_stream(LOG_GROUP_NAME, log_stream)
                
                # CloudWatch has a limit of 10,000 events per put, split if needed
                batch_size = 10000
                for i in range(0, len(log_events), batch_size):
                    batch = log_events[i:i + batch_size]
                    put_log_events(LOG_GROUP_NAME, log_stream, batch)
                
                print(f"Wrote {len(log_events)} events to {LOG_GROUP_NAME}/{log_stream}")
        
        except Exception as e:
            print(f"Error processing record: {e}")
            error_count += 1
    
    result = {
        "statusCode": 200,
        "body": {
            "processed": processed_count,
            "skipped": skipped_count,
            "errors": error_count,
            "log_group": LOG_GROUP_NAME,
        }
    }
    
    print(f"Result: {json.dumps(result)}")
    return result
