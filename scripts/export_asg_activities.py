"""
Export ASG scaling activities to JSONL format.

Usage:
  python scripts/export_asg_activities.py --asg-name course-management-asg-dev --output data/logs/asg/asg_activities_20251203.jsonl
"""
import boto3
import json
import argparse
from datetime import datetime
from pathlib import Path


def export_asg_activities(asg_name: str, output_path: str, region: str = "us-east-1"):
    """Fetch ASG scaling activities and save as JSONL."""
    client = boto3.client("autoscaling", region_name=region)
    
    print(f"Fetching scaling activities for ASG: {asg_name}")
    response = client.describe_scaling_activities(
        AutoScalingGroupName=asg_name,
        MaxRecords=100  # adjust as needed
    )
    
    activities = response.get("Activities", [])
    print(f"Found {len(activities)} activities")
    
    # Create output directory if needed
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for activity in activities:
            record = {
                "timestamp": activity.get("StartTime").isoformat() if activity.get("StartTime") else None,
                "end_time": activity.get("EndTime").isoformat() if activity.get("EndTime") else None,
                "activity_id": activity.get("ActivityId"),
                "status": activity.get("StatusCode"),
                "status_message": activity.get("StatusMessage"),
                "cause": activity.get("Cause"),
                "description": activity.get("Description"),
                "details": activity.get("Details"),
                "progress": activity.get("Progress"),
                "component": "asg",
                "asg_name": asg_name,
                "region": region,
                "environment": "dev",
                "service_name": "course-management-system",
                "severity": "CRITICAL" if activity.get("StatusCode") == "Failed" else "INFO",
                "event_type": "scaling" if "Launching" in activity.get("Description", "") or "Terminating" in activity.get("Description", "") else "other",
                "tags": {"project": "course-management", "managed_by": "terraform"},
            }
            f.write(json.dumps(record) + "\n")
    
    print(f"Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Export ASG scaling activities to JSONL")
    parser.add_argument("--asg-name", required=True, help="Auto Scaling Group name")
    parser.add_argument("--output", required=True, help="Output JSONL file path")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    
    args = parser.parse_args()
    export_asg_activities(args.asg_name, args.output, args.region)


if __name__ == "__main__":
    main()
