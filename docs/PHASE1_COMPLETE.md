# Phase 1 Data Collection - Status

## Completed Exports

### ✅ CloudWatch Alarms
- File: `data/alarms/alarms_20251203.jsonl`
- Count: 11 alarms with definitions + 7 days history
- Status: **Success**

### ⚠️ ALB Access Logs
- Status: **Skipped** - Log group not found in CloudWatch Logs
- **Reason**: ALB typically logs directly to S3, not CloudWatch Logs
- **Next Steps**: 
  - Enable ALB access logs to S3 in AWS Console (ALB → Attributes → Access logs)
  - OR: If already enabled, use S3 files directly (no export needed)
  - Typical path: `s3://<bucket>/<prefix>/AWSLogs/<account>/elasticloadbalancing/<region>/YYYY/MM/DD/`

### ✅ Runbook Created
- File: `data/docs/ALB_ASG_Runbook.md`
- Topics: Health checks, scaling lag, 5xx errors, deployments, cost spikes
- Status: **Complete**

## ASG Activities Export

Run this command to export ASG scaling activities:

```powershell
python scripts/export_asg_activities.py --asg-name course-management-asg-dev --output data/logs/asg/asg_activities_20251203.jsonl
```

## ALB Logs Alternative (if not in CloudWatch)

### Option 1: Enable ALB → S3 logging
1. Go to EC2 Console → Load Balancers
2. Select your ALB → Attributes tab
3. Enable "Access logs" → specify S3 bucket
4. Wait 5-10 minutes for logs to appear
5. Download and use those files (already in parseable format)

### Option 2: Create synthetic sample data for demo
If you just need demo data and don't have real traffic yet, I can generate a small synthetic ALB log file.

## Data Organization

Current structure:
```
data/
├── alarms/
│   └── alarms_20251203.jsonl ✅
├── docs/
│   └── ALB_ASG_Runbook.md ✅
└── logs/
    ├── alb/
    │   └── (empty - needs ALB logs from S3 or synthetic)
    └── asg/
        └── (pending - run export command above)
```

## Next Steps

1. Run ASG activities export
2. Either:
   - Enable ALB → S3 logs and download, OR
   - Use synthetic sample data for demo
3. Proceed to Phase 2: Upload to S3 for Bedrock KB

## Fixed Issues
- ✅ Removed datetime.utcnow() deprecation warnings (now using timezone-aware datetime)
