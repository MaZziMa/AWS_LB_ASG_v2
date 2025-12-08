"""
Export ALB access logs from CloudWatch Logs to JSONL format.

Note: If ALB logs are already in S3, you can skip this and use them directly.
This script is for exporting from CloudWatch Logs if that's where they are.

Usage:
  python scripts/export_alb_logs.py --log-group /aws/elasticloadbalancing/app/course-management-alb --output data/logs/alb/alb_20251203.jsonl --hours 24
"""
import boto3
import json
import argparse
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_alb_log_line(line: str) -> dict:
    """Parse ALB access log line into structured record.
    
    ALB log format: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-access-logs.html
    """
    # Simplified parser - adjust regex for your exact format
    # Example line: 2023-12-03T15:30:00.123456Z app/my-alb/xxx 1.2.3.4:12345 10.0.1.5:80 0.001 0.002 0.000 200 200 123 456 "GET http://example.com:80/path HTTP/1.1" ...
    
    parts = line.split()
    if len(parts) < 15:
        return None
    
    try:
        return {
            "timestamp": parts[1],
            "elb": parts[2],
            "client_ip": parts[3].split(":")[0],
            "client_port": parts[3].split(":")[1] if ":" in parts[3] else None,
            "target_ip": parts[4].split(":")[0] if parts[4] != "-" else None,
            "target_port": parts[4].split(":")[1] if ":" in parts[4] and parts[4] != "-" else None,
            "request_processing_time": float(parts[5]) if parts[5] != "-1" else None,
            "target_processing_time": float(parts[6]) if parts[6] != "-1" else None,
            "response_processing_time": float(parts[7]) if parts[7] != "-1" else None,
            "elb_status_code": int(parts[8]) if parts[8] != "-" else None,
            "target_status_code": int(parts[9]) if parts[9] != "-" else None,
            "received_bytes": int(parts[10]) if parts[10] != "-" else None,
            "sent_bytes": int(parts[11]) if parts[11] != "-" else None,
            "request_verb": parts[12].strip('"') if len(parts) > 12 else None,
            "request_url": parts[13] if len(parts) > 13 else None,
            "request_proto": parts[14].strip('"') if len(parts) > 14 else None,
            "component": "alb",
        }
    except Exception as e:
        print(f"Warning: Failed to parse line: {e}")
        return None


def export_alb_logs_from_cloudwatch(log_group: str, output_path: str, region: str, hours: int):
    """Fetch ALB logs from CloudWatch Logs and save as JSONL."""
    client = boto3.client("logs", region_name=region)
    
    start_time = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp() * 1000)
    end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    print(f"Fetching logs from {log_group} for last {hours} hours...")
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        try:
            # Start query
            query = "fields @timestamp, @message | sort @timestamp desc | limit 10000"
            response = client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=query
            )
            query_id = response["queryId"]
            
            # Wait for results
            import time
            while True:
                result = client.get_query_results(queryId=query_id)
                status = result["status"]
                if status in ["Complete", "Failed", "Cancelled"]:
                    break
                time.sleep(1)
            
            if status != "Complete":
                print(f"Query failed with status: {status}")
                return
            
            # Process results
            for row in result.get("results", []):
                message = None
                timestamp = None
                for field in row:
                    if field["field"] == "@message":
                        message = field["value"]
                    elif field["field"] == "@timestamp":
                        timestamp = field["value"]
                
                if message:
                    parsed = parse_alb_log_line(message)
                    if parsed:
                        if timestamp:
                            parsed["timestamp"] = timestamp
                        f.write(json.dumps(parsed) + "\n")
            
            print(f"Exported to {output_path}")
        
        except client.exceptions.ResourceNotFoundException:
            print(f"Error: Log group {log_group} not found")
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Export ALB logs from CloudWatch to JSONL")
    parser.add_argument("--log-group", required=True, help="CloudWatch log group name")
    parser.add_argument("--output", required=True, help="Output JSONL file path")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--hours", type=int, default=24, help="Hours of logs to fetch")
    
    args = parser.parse_args()
    export_alb_logs_from_cloudwatch(args.log_group, args.output, args.region, args.hours)


if __name__ == "__main__":
    main()
