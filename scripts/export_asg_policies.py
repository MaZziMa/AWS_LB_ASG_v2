#!/usr/bin/env python3
"""
Export Auto Scaling Group scaling policies and configuration.
Captures scaling thresholds, cooldowns, and policy details.
"""
import boto3
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any


def export_asg_policies(
    asg_name: str,
    output_file: str,
    region: str = "us-east-1",
):
    """Export ASG scaling policies to JSONL."""
    asg = boto3.client("autoscaling", region_name=region)
    cloudwatch = boto3.client("cloudwatch", region_name=region)
    
    print(f"Fetching ASG configuration: {asg_name}")
    asg_response = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    
    if not asg_response["AutoScalingGroups"]:
        raise ValueError(f"ASG {asg_name} not found")
    
    asg_config = asg_response["AutoScalingGroups"][0]
    
    records = []
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # ASG configuration record
    config_record = {
        "record_type": "asg_configuration",
        "timestamp": timestamp,
        "asg_name": asg_name,
        "min_size": asg_config["MinSize"],
        "max_size": asg_config["MaxSize"],
        "desired_capacity": asg_config["DesiredCapacity"],
        "default_cooldown": asg_config["DefaultCooldown"],
        "health_check_type": asg_config["HealthCheckType"],
        "health_check_grace_period": asg_config["HealthCheckGracePeriod"],
        "availability_zones": asg_config["AvailabilityZones"],
        "load_balancer_names": asg_config.get("LoadBalancerNames", []),
        "target_group_arns": asg_config.get("TargetGroupARNs", []),
        "instance_count": len(asg_config["Instances"]),
        "region": region,
        "environment": "dev",
        "service_name": "course-management-system",
        "component": "auto-scaling-group",
        "capacity_utilization": round((asg_config["DesiredCapacity"] / asg_config["MaxSize"]) * 100, 1),
        "tags": {"project": "course-management", "managed_by": "terraform"},
    }
    records.append(config_record)
    
    # Scaling policies
    print("Fetching scaling policies...")
    policies_response = asg.describe_policies(AutoScalingGroupName=asg_name)
    
    for policy in policies_response["ScalingPolicies"]:
        policy_record = {
            "record_type": "asg_scaling_policy",
            "timestamp": timestamp,
            "asg_name": asg_name,
            "policy_name": policy["PolicyName"],
            "policy_arn": policy["PolicyARN"],
            "policy_type": policy["PolicyType"],
            "adjustment_type": policy.get("AdjustmentType"),
            "scaling_adjustment": policy.get("ScalingAdjustment"),
            "cooldown": policy.get("Cooldown"),
            "min_adjustment_magnitude": policy.get("MinAdjustmentMagnitude"),
            "target_tracking_config": policy.get("TargetTrackingConfiguration"),
            "step_adjustments": policy.get("StepAdjustments"),
            "region": region,
            "environment": "dev",
            "service_name": "course-management-system",
            "component": "auto-scaling-group",
            "scaling_direction": "up" if policy.get("ScalingAdjustment", 0) > 0 else "down",
            "tags": {"project": "course-management"},
        }
        records.append(policy_record)
        
        # Fetch associated CloudWatch alarms
        if "Alarms" in policy:
            for alarm in policy["Alarms"]:
                alarm_name = alarm["AlarmName"]
                alarm_response = cloudwatch.describe_alarms(AlarmNames=[alarm_name])
                
                if alarm_response["MetricAlarms"]:
                    alarm_detail = alarm_response["MetricAlarms"][0]
                    alarm_record = {
                        "record_type": "asg_policy_alarm",
                        "timestamp": timestamp,
                        "asg_name": asg_name,
                        "policy_name": policy["PolicyName"],
                        "alarm_name": alarm_name,
                        "alarm_arn": alarm_detail["AlarmArn"],
                        "metric_name": alarm_detail.get("MetricName"),
                        "namespace": alarm_detail.get("Namespace"),
                        "statistic": alarm_detail.get("Statistic"),
                        "comparison_operator": alarm_detail.get("ComparisonOperator"),
                        "threshold": alarm_detail.get("Threshold"),
                        "evaluation_periods": alarm_detail.get("EvaluationPeriods"),
                        "period": alarm_detail.get("Period"),
                        "alarm_state": alarm_detail["StateValue"],
                        "region": region,
                        "environment": "dev",
                    }
                    records.append(alarm_record)
    
    # Scheduled actions
    print("Fetching scheduled actions...")
    scheduled_response = asg.describe_scheduled_actions(AutoScalingGroupName=asg_name)
    
    for action in scheduled_response["ScheduledUpdateGroupActions"]:
        scheduled_record = {
            "record_type": "asg_scheduled_action",
            "timestamp": timestamp,
            "asg_name": asg_name,
            "scheduled_action_name": action["ScheduledActionName"],
            "scheduled_action_arn": action["ScheduledActionARN"],
            "start_time": action.get("StartTime", "").isoformat() if action.get("StartTime") else None,
            "end_time": action.get("EndTime", "").isoformat() if action.get("EndTime") else None,
            "recurrence": action.get("Recurrence"),
            "min_size": action.get("MinSize"),
            "max_size": action.get("MaxSize"),
            "desired_capacity": action.get("DesiredCapacity"),
            "region": region,
            "environment": "dev",
        }
        records.append(scheduled_record)
    
    # Create output directory if needed
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Write to JSONL
    with open(output_file, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    
    print(f"Exported {len(records)} records to {output_file}")
    print(f"  - 1 ASG configuration")
    print(f"  - {len(policies_response['ScalingPolicies'])} scaling policies")
    print(f"  - {len(scheduled_response['ScheduledUpdateGroupActions'])} scheduled actions")


def main():
    parser = argparse.ArgumentParser(
        description="Export ASG scaling policies and configuration"
    )
    parser.add_argument(
        "--asg-name",
        required=True,
        help="Auto Scaling Group name",
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
    export_asg_policies(args.asg_name, args.output, args.region)


if __name__ == "__main__":
    main()
