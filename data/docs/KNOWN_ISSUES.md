# Known Issues & Troubleshooting Guide

This document catalogs common failure patterns, root causes, and resolutions for the Course Management System.

## Issue #1: Health Check Failures During Deployment

**Last Occurrence**: Multiple deployments (Nov 2025)

**Symptoms**:
- Targets marked unhealthy immediately after launch
- 502 Bad Gateway errors during instance replacement
- ASG terminates new instances before they're ready

**Root Cause**:
Health check grace period (300s) insufficient for application startup. FastAPI app takes ~180s to:
- Install pip dependencies
- Load DynamoDB connection pool
- Start Uvicorn server

**Resolution**:
- Increased health check grace period from 180s → 300s
- Optimized user data script to use AMI with pre-installed dependencies
- Added `/health` endpoint early return (before heavy initialization)

**Prevention**:
- Use custom AMI with dependencies baked in (launch time: 30s)
- Implement graceful startup checks in /health endpoint
- Monitor `UnhealthyHostCount` metric during deployments

---

## Issue #2: CPU Spike After Midnight Backups

**Last Occurrence**: Dec 1, 2025 00:15 UTC

**Symptoms**:
- CPU utilization → 85% at midnight
- ASG scales from 2 → 4 instances
- DynamoDB throttling errors
- Elevated P99 latency (500ms → 2000ms)

**Root Cause**:
Scheduled DynamoDB backup job runs at midnight, causing:
- Full table scans on `enrollments` table
- High read capacity consumption
- CPU spike on EC2 instances processing large result sets

**Resolution**:
- Enabled DynamoDB Point-in-Time Recovery (no scan required)
- Disabled manual backup Lambda function
- CPU returned to baseline within 10 minutes

**Prevention**:
- Use PITR instead of on-demand backups
- Implement pagination for large table scans
- Add query filters to reduce result set size
- Monitor `ConsumedReadCapacityUnits` metric

---

## Issue #3: Intermittent 504 Gateway Timeout

**Last Occurrence**: Nov 28, 2025 14:30 UTC

**Symptoms**:
- Random 504 errors on `/courses` endpoint
- ALB access logs show `elb_status_code: 504`
- Application logs show no errors
- Occurs 1-2 times per hour during peak traffic

**Root Cause**:
ALB idle timeout (60s) shorter than DynamoDB query timeout. When DynamoDB experiences latency spikes:
- Query takes >60s to complete
- ALB terminates connection
- Application continues processing (wasted resources)

**Resolution**:
- Increased ALB idle timeout: 60s → 120s
- Added application-level timeout (90s) with graceful error handling
- Implemented DynamoDB query retry with exponential backoff

**Prevention**:
- Set application timeout < ALB timeout < client timeout
- Monitor `TargetResponseTime` P99 metric
- Add query timeout CloudWatch alarm (>50s)
- Use DynamoDB query pagination to avoid long-running queries

---

## Issue #4: Scale-Down Too Aggressive

**Last Occurrence**: Nov 25, 2025 10:00 UTC

**Symptoms**:
- ASG scales down from 3 → 1 instance during morning traffic
- Sudden latency spike (100ms → 800ms)
- Single instance CPU → 75%
- Manual scale-up required

**Root Cause**:
Scale-down policy too aggressive:
- Threshold: CPU < 30% for 10 minutes
- Morning lull (9:00-9:30) triggered scale-down
- Traffic resumed at 9:30, but new instance takes 5 minutes to launch

**Resolution**:
- Changed scale-down threshold: 30% → 20%
- Increased evaluation period: 10 min → 30 min
- Added scheduled scaling action: keep min=2 during business hours (8am-6pm)

**Prevention**:
- Use scheduled scaling for predictable traffic patterns
- Set conservative scale-down thresholds
- Monitor `CPUUtilization` and `TargetResponseTime` together
- Implement step scaling (remove 1 instance at a time, not 50%)

---

## Issue #5: DynamoDB Hot Partition

**Last Occurrence**: Nov 22, 2025 16:45 UTC

**Symptoms**:
- `ProvisionedThroughputExceededException` errors
- Specific course ID queries failing
- Other queries working normally
- Sporadic 500 errors for popular courses

**Root Cause**:
Popular course (course_id: "CS101") receiving 80% of queries:
- DynamoDB partitions by primary key (course_id)
- Single partition maxed out at 3000 RCU
- Hot partition throttled while other partitions idle

**Resolution**:
- Switched DynamoDB pricing model: Provisioned → On-Demand
- Added DynamoDB DAX (in-memory cache) for popular courses
- Implemented application-level caching (Redis) for course details

**Prevention**:
- Use on-demand pricing for unpredictable traffic
- Implement read replicas or caching layer
- Monitor `UserErrors` metric for throttling
- Design keys to distribute load evenly (composite keys)

---

## Issue #6: Instance Termination Mid-Request

**Last Occurrence**: Nov 20, 2025 12:10 UTC

**Symptoms**:
- Random 502 errors during scale-down events
- ALB logs show `target_status_code: -` (connection reset)
- ~5-10 failed requests per scale-down

**Root Cause**:
ASG terminates instances immediately without waiting for in-flight requests:
- ALB connection draining: 300s (correct)
- Application not handling SIGTERM gracefully
- Uvicorn shuts down immediately, dropping active connections

**Resolution**:
- Updated systemd service to use `TimeoutStopSec=310` (> connection draining)
- Modified application to handle SIGTERM:
  ```python
  @app.on_event("shutdown")
  async def graceful_shutdown():
      await asyncio.sleep(5)  # Allow final requests
      logger.info("Graceful shutdown complete")
  ```
- Verified ALB deregistration delay: 30s

**Prevention**:
- Implement graceful shutdown in application code
- Test connection draining with `curl --max-time` during scale-down
- Monitor `HTTPCode_Target_5XX_Count` during ASG activities
- Set application shutdown timeout > ALB draining timeout

---

## Issue #7: Out of Memory Kills

**Last Occurrence**: Nov 18, 2025 08:30 UTC

**Symptoms**:
- Instance terminated by EC2 health check
- CloudWatch Logs show "Killed" message
- No application error logs
- Memory utilization → 100% before termination

**Root Cause**:
Memory leak in FastAPI application:
- SQLAlchemy connection pool not closing connections
- Each request creates new DynamoDB client (boto3)
- 1000+ requests → 1 GB RAM exhausted on t3.micro

**Resolution**:
- Implemented singleton pattern for boto3 clients (reuse)
- Added connection pool limits: max_pool_connections=10
- Upgraded instance type: t3.micro (1 GB) → t3.small (2 GB)
- Added memory monitoring with CloudWatch agent

**Prevention**:
- Profile memory usage under load testing
- Set memory limits in systemd: `MemoryMax=1.5G`
- Monitor `mem_used_percent` metric
- Implement connection pooling for all external clients

---

## Issue #8: SSL Certificate Expiration

**Last Occurrence**: N/A (prevented)

**Symptoms** (if occurred):
- HTTPS endpoints return connection errors
- Browser shows "certificate expired" warning
- ALB health checks fail if using HTTPS

**Root Cause**:
ACM certificate auto-renewal requires:
- DNS validation records in Route 53
- Email verification for domain owner
- 60-day renewal window

**Resolution** (preventive):
- Use ACM certificates (auto-renew if DNS validated)
- Set CloudWatch alarm for `DaysToExpiry < 30`
- Document manual renewal process in runbook

**Prevention**:
- Always use DNS validation (not email)
- Monitor ACM certificate expiration
- Test renewal process in staging
- Keep domain contact emails up-to-date

---

## Troubleshooting Checklist

When investigating issues, check in this order:

1. **CloudWatch Alarms**: Are any alarms in ALARM state?
2. **ALB Target Health**: Are all targets healthy?
3. **ASG Activity History**: Any recent scaling events or instance replacements?
4. **CloudWatch Metrics**: CPU, memory, network spikes?
5. **ALB Access Logs**: HTTP status codes, response times, target IPs
6. **Application Logs**: Errors, exceptions, stack traces
7. **DynamoDB Metrics**: Throttling, consumed capacity, user errors
8. **Recent Deployments**: Code changes, config updates, infrastructure changes

## Escalation Procedure

1. **Severity 1 (System Down)**: Page on-call engineer, rollback deployment if within 1 hour
2. **Severity 2 (Degraded Performance)**: Notify team Slack, investigate within 30 minutes
3. **Severity 3 (Isolated Issues)**: Create ticket, investigate during business hours
4. **Severity 4 (Cosmetic)**: Backlog for next sprint

## Useful Commands

```bash
# Check target health
aws elbv2 describe-target-health --target-group-arn <TG_ARN>

# View recent ASG activities
aws autoscaling describe-scaling-activities --auto-scaling-group-name course-management-asg-dev --max-records 20

# Query ALB access logs (S3)
aws s3 cp s3://course-management-bedrock-kb-dev/bedrock/logs/alb/ . --recursive

# Check EC2 instance system logs
aws ec2 get-console-output --instance-id <INSTANCE_ID>

# Test application endpoint
curl -i http://course-management-alb-dev-1530526851.us-east-1.elb.amazonaws.com/health
```

## References
- ALB Troubleshooting: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html
- ASG Troubleshooting: https://docs.aws.amazon.com/autoscaling/ec2/userguide/CHAP_Troubleshooting.html
- DynamoDB Troubleshooting: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html
