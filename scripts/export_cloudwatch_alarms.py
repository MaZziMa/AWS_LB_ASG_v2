"""
Export CloudWatch alarm definitions and history to JSONL.

Usage:
  python scripts/export_cloudwatch_alarms.py --output data/alarms/alarms_20251203.jsonl
"""
import boto3
import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path


def export_alarms(output_path: str, region: str = "us-east-1", history_days: int = 7):
    """Fetch CloudWatch alarms and their history, save as JSONL."""
    client = boto3.client("cloudwatch", region_name=region)
    
    print("Fetching CloudWatch alarms...")
    alarms_response = client.describe_alarms(MaxRecords=100)
    alarms = alarms_response.get("MetricAlarms", [])
    print(f"Found {len(alarms)} alarms")
    
    # Create output directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        # Export alarm definitions
        for alarm in alarms:
            record = {
                "type": "alarm_definition",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alarm_name": alarm.get("AlarmName"),
                "alarm_arn": alarm.get("AlarmArn"),
                "description": alarm.get("AlarmDescription"),
                "metric_name": alarm.get("MetricName"),
                "namespace": alarm.get("Namespace"),
                "statistic": alarm.get("Statistic"),
                "period": alarm.get("Period"),
                "evaluation_periods": alarm.get("EvaluationPeriods"),
                "threshold": alarm.get("Threshold"),
                "comparison_operator": alarm.get("ComparisonOperator"),
                "state_value": alarm.get("StateValue"),
                "state_reason": alarm.get("StateReason"),
                "state_updated_timestamp": alarm.get("StateUpdatedTimestamp").isoformat() if alarm.get("StateUpdatedTimestamp") else None,
                "actions_enabled": alarm.get("ActionsEnabled"),
                "alarm_actions": alarm.get("AlarmActions", []),
                "dimensions": alarm.get("Dimensions", []),
                "component": "cloudwatch_alarm",
                "region": region,
                "environment": "dev",
                "service_name": "course-management-system",
                "severity": "CRITICAL" if alarm.get("StateValue") == "ALARM" else "INFO",
                "alert_priority": "high" if "5XX" in alarm.get("AlarmName", "") or "Unhealthy" in alarm.get("AlarmName", "") else "medium",
                "tags": {"project": "course-management", "monitored": "true"},
            }
            f.write(json.dumps(record) + "\n")
            
            # Fetch history for this alarm
            try:
                start_date = datetime.now(timezone.utc) - timedelta(days=history_days)
                history_response = client.describe_alarm_history(
                    AlarmName=alarm["AlarmName"],
                    StartDate=start_date,
                    MaxRecords=50
                )
                
                for history_item in history_response.get("AlarmHistoryItems", []):
                    history_record = {
                        "type": "alarm_history",
                        "alarm_name": alarm["AlarmName"],
                        "timestamp": history_item.get("Timestamp").isoformat() if history_item.get("Timestamp") else None,
                        "history_item_type": history_item.get("HistoryItemType"),
                        "history_summary": history_item.get("HistorySummary"),
                        "history_data": json.loads(history_item.get("HistoryData", "{}")),
                        "component": "cloudwatch_alarm_history",
                        "region": region,
                        "environment": "dev",
                        "service_name": "course-management-system",
                        "event_type": "state_change" if history_item.get("HistoryItemType") == "StateUpdate" else "config_change",
                        "tags": {"project": "course-management"},
                    }
                    f.write(json.dumps(history_record) + "\n")
            except Exception as e:
                print(f"Warning: Could not fetch history for {alarm['AlarmName']}: {e}")
    
    print(f"Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Export CloudWatch alarms and history to JSONL")
    parser.add_argument("--output", required=True, help="Output JSONL file path")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--history-days", type=int, default=7, help="Days of history to fetch")
    
    args = parser.parse_args()
    export_alarms(args.output, args.region, args.history_days)


if __name__ == "__main__":
    main()
