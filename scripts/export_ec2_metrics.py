#!/usr/bin/env python3
"""
Export EC2 CloudWatch metrics for instances in an Auto Scaling Group.
Fetches CPU, Memory, Network, and Disk metrics for KB ingestion.
"""
import boto3
import json
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any


def get_asg_instances(asg_name: str, region: str) -> List[str]:
    """Get list of instance IDs from Auto Scaling Group."""
    asg = boto3.client("autoscaling", region_name=region)
    response = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    
    if not response["AutoScalingGroups"]:
        raise ValueError(f"ASG {asg_name} not found")
    
    instances = response["AutoScalingGroups"][0]["Instances"]
    return [inst["InstanceId"] for inst in instances if inst["LifecycleState"] == "InService"]


def fetch_metric(
    cloudwatch,
    namespace: str,
    metric_name: str,
    dimensions: List[Dict[str, str]],
    start_time: datetime,
    end_time: datetime,
    stat: str = "Average",
    period: int = 300,
) -> List[Dict[str, Any]]:
    """Fetch CloudWatch metric statistics."""
    response = cloudwatch.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=period,
        Statistics=[stat],
    )
    return response["Datapoints"]


def export_ec2_metrics(
    asg_name: str,
    hours: int,
    output_file: str,
    region: str = "us-east-1",
):
    """Export EC2 metrics for all instances in ASG to JSONL."""
    print(f"Fetching instances from ASG: {asg_name}")
    instance_ids = get_asg_instances(asg_name, region)
    print(f"Found {len(instance_ids)} in-service instances: {instance_ids}")
    
    cloudwatch = boto3.client("cloudwatch", region_name=region)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    metrics_config = [
        ("AWS/EC2", "CPUUtilization", "%", "Average"),
        ("AWS/EC2", "NetworkIn", "Bytes", "Sum"),
        ("AWS/EC2", "NetworkOut", "Bytes", "Sum"),
        ("AWS/EC2", "StatusCheckFailed", "Count", "Sum"),
        ("AWS/EC2", "StatusCheckFailed_Instance", "Count", "Sum"),
        ("AWS/EC2", "StatusCheckFailed_System", "Count", "Sum"),
    ]
    
    records = []
    
    for instance_id in instance_ids:
        print(f"Fetching metrics for instance: {instance_id}")
        dimensions = [{"Name": "InstanceId", "Value": instance_id}]
        
        for namespace, metric_name, unit, stat in metrics_config:
            datapoints = fetch_metric(
                cloudwatch,
                namespace,
                metric_name,
                dimensions,
                start_time,
                end_time,
                stat=stat,
                period=300,  # 5-minute intervals
            )
            
            for dp in datapoints:
                record = {
                    "record_type": "ec2_metric",
                    "timestamp": dp["Timestamp"].isoformat(),
                    "instance_id": instance_id,
                    "asg_name": asg_name,
                    "metric_name": metric_name,
                    "value": dp[stat],
                    "unit": unit,
                    "statistic": stat,
                    "region": region,
                    "environment": "dev",
                    "service_name": "course-management-system",
                    "component": "ec2-instances",
                    "severity": "WARNING" if (metric_name == "CPUUtilization" and dp[stat] > 70) or (metric_name.startswith("StatusCheckFailed") and dp[stat] > 0) else "INFO",
                    "tags": {"project": "course-management", "instance_type": "t3.micro"},
                }
                records.append(record)
    
    # Sort by timestamp
    records.sort(key=lambda x: x["timestamp"])
    
    # Create output directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write to JSONL
    with open(output_file, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    
    print(f"Exported {len(records)} metric datapoints to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Export EC2 CloudWatch metrics for ASG instances"
    )
    parser.add_argument(
        "--asg-name",
        required=True,
        help="Auto Scaling Group name",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours of metrics to export (default: 24)",
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
    export_ec2_metrics(args.asg_name, args.hours, args.output, args.region)


if __name__ == "__main__":
    main()
