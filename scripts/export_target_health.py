#!/usr/bin/env python3
"""
Export ALB Target Group health check history.
Tracks target health transitions for troubleshooting.
"""
import boto3
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any


def get_target_group_arn(tg_name: str, region: str) -> str:
    """Get Target Group ARN from name."""
    elbv2 = boto3.client("elbv2", region_name=region)
    response = elbv2.describe_target_groups(Names=[tg_name])
    
    if not response["TargetGroups"]:
        raise ValueError(f"Target Group {tg_name} not found")
    
    return response["TargetGroups"][0]["TargetGroupArn"]


def get_target_health_history(tg_arn: str, region: str) -> List[Dict[str, Any]]:
    """Get current target health status."""
    elbv2 = boto3.client("elbv2", region_name=region)
    response = elbv2.describe_target_health(TargetGroupArn=tg_arn)
    
    records = []
    timestamp = datetime.now(timezone.utc).isoformat()
    
    for target_health in response["TargetHealthDescriptions"]:
        target = target_health["Target"]
        health = target_health["TargetHealth"]
        
        record = {
            "record_type": "target_health",
            "timestamp": timestamp,
            "target_id": target["Id"],
            "target_port": target.get("Port", 8000),
            "availability_zone": target.get("AvailabilityZone"),
            "health_state": health["State"],
            "health_reason": health.get("Reason", "N/A"),
            "health_description": health.get("Description", "N/A"),
            "target_group_arn": tg_arn,
            "region": region,
            "environment": "dev",
            "service_name": "course-management-system",
            "component": "alb-target-group",
            "severity": "CRITICAL" if health["State"] == "unhealthy" else "INFO",
            "alert_required": health["State"] in ["unhealthy", "draining"],
            "tags": {"project": "course-management", "load_balancer": "course-management-alb-dev"},
        }
        records.append(record)
    
    return records


def export_target_health(
    tg_name: str,
    output_file: str,
    region: str = "us-east-1",
):
    """Export target health status to JSONL."""
    print(f"Fetching Target Group ARN for: {tg_name}")
    tg_arn = get_target_group_arn(tg_name, region)
    print(f"Target Group ARN: {tg_arn}")
    
    print("Fetching target health status...")
    records = get_target_health_history(tg_arn, region)
    
    # Create output directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write to JSONL
    with open(output_file, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    
    print(f"Exported {len(records)} target health records to {output_file}")
    
    # Summary
    healthy = sum(1 for r in records if r["health_state"] == "healthy")
    unhealthy = sum(1 for r in records if r["health_state"] == "unhealthy")
    print(f"Summary: {healthy} healthy, {unhealthy} unhealthy")


def main():
    parser = argparse.ArgumentParser(
        description="Export ALB Target Group health status"
    )
    parser.add_argument(
        "--target-group",
        required=True,
        help="Target Group name",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )
    
    args = parser.parse_args()
    export_target_health(args.target_group, args.output, args.region)


if __name__ == "__main__":
    main()
