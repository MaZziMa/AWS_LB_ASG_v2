# ALB & ASG Operations Runbook

## Overview
This runbook provides troubleshooting steps for common Application Load Balancer (ALB) and Auto Scaling Group (ASG) operational issues in the Course Management System infrastructure.

## Health Check Failures

### Symptoms
- Targets marked unhealthy in ALB Target Group
- Instances terminated and replaced by ASG
- Intermittent 502/503 errors from ALB

### Diagnosis Steps
1. Check ALB target health:
   ```bash
   aws elbv2 describe-target-health --target-group-arn <ARN> --region us-east-1
   ```

2. Review application logs on the instance:
   ```bash
   ssh ec2-user@<instance-ip>
   sudo journalctl -u course-app -n 100 --no-pager
   ```

3. Test health endpoint directly:
   ```bash
   curl -v http://<instance-ip>:8000/health
   ```

4. Check health check configuration:
   - Path: `/health`
   - Expected: 200 OK response
   - Interval: 15-30 seconds
   - Timeout: 5 seconds
   - Healthy/Unhealthy thresholds: 2-3 consecutive checks

### Common Causes
- Application startup slower than health check grace period
- Insufficient instance resources (CPU/memory)
- Application crash or deadlock
- Security group blocking ALB health checks
- DynamoDB access denied (IAM permissions)

### Remediation
- **Fast fix**: Increase `health_check_grace_period` in ASG (e.g., 90-120s)
- **App issue**: Check gunicorn workers, increase if needed
- **Startup lag**: Use prebaked AMI with Packer, enable warm pool
- **Security**: Verify security group allows ALB subnet → instance port 8000
- **IAM**: Confirm instance role has DynamoDB read/write permissions

## ASG Scaling Lag

### Symptoms
- Traffic spike but ASG doesn't scale out quickly
- High CPU/RequestCount but desired capacity unchanged
- Scaling activities show "WaitingForInstanceWarmup"

### Diagnosis Steps
1. Check current ASG status:
   ```bash
   aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names course-management-asg-dev --region us-east-1
   ```

2. Review recent scaling activities:
   ```bash
   aws autoscaling describe-scaling-activities --auto-scaling-group-name course-management-asg-dev --max-records 20 --region us-east-1
   ```

3. Check CloudWatch alarms:
   ```bash
   aws cloudwatch describe-alarms --alarm-names high-cpu-alarm --region us-east-1
   ```

4. Review metrics:
   - CPU Utilization (last 15 minutes)
   - ALBRequestCountPerTarget
   - ALBTargetResponseTime

### Common Causes
- Alarm period/evaluation periods too long (e.g., 5 minutes)
- `default_instance_warmup` too long (delays new capacity)
- Warm pool disabled or empty
- Cooldown periods preventing scale actions
- Insufficient capacity (max size reached)

### Remediation
- **Faster detection**: Reduce alarm period to 60s, evaluationPeriods to 1-2
- **Faster capacity**: Lower `default_instance_warmup` to 60-90s (if startup is fast)
- **Pre-warmed instances**: Enable warm pool with min size 1-2
- **Target tracking**: Use `ALBRequestCountPerTarget` instead of CPU for traffic-based scaling
- **Capacity limits**: Increase ASG max size if legitimate traffic growth

## High 5xx Error Rate

### Symptoms
- ALB returning 502/503/504 errors
- Target response time spikes
- Client complaints about timeouts

### Diagnosis Steps
1. Check ALB metrics in CloudWatch:
   - HTTPCode_Target_5XX_Count
   - TargetResponseTime (P50, P90, P99)
   - HealthyHostCount

2. Review ALB access logs (last hour):
   - Filter for status codes 5xx
   - Identify affected paths/targets

3. Check target logs for errors:
   ```bash
   ssh ec2-user@<instance-ip>
   sudo journalctl -u course-app --since "1 hour ago" | grep -i error
   ```

4. Verify database connectivity:
   ```bash
   aws dynamodb describe-table --table-name courses --region us-east-1
   ```

### Common Causes
- Target overload (insufficient capacity during spike)
- Application errors (exceptions, crashes)
- DynamoDB throttling (provisioned throughput exceeded)
- Long-running requests timeout (ALB idle timeout 60s default)
- Target draining during deployment

### Remediation
- **Capacity**: Scale out ASG manually or adjust scaling policies
- **App errors**: Review logs, fix bugs, redeploy
- **DynamoDB**: Switch to on-demand billing or increase provisioned capacity
- **Timeouts**: Optimize slow endpoints, increase ALB idle timeout if needed
- **Deployment**: Use MinHealthyPercentage 75% for instance refresh

## Deployment Issues

### Symptoms
- Instance refresh stuck at 0% progress
- New instances fail health checks repeatedly
- Rollback required

### Diagnosis Steps
1. Check instance refresh status:
   ```bash
   aws autoscaling describe-instance-refreshes --auto-scaling-group-name course-management-asg-dev --region us-east-1
   ```

2. Review recent launch template changes:
   ```bash
   aws ec2 describe-launch-template-versions --launch-template-id <id> --region us-east-1
   ```

3. Test new AMI manually:
   - Launch instance with new AMI
   - SSH and check application startup
   - Curl health endpoint

### Common Causes
- Bad AMI (app fails to start)
- Incorrect user_data script
- AMI missing dependencies
- Security group changes blocking traffic
- IAM role missing new permissions

### Remediation
- **Bad AMI**: Roll back to previous AMI in terraform.tfvars, reapply
- **Fix & rebuild**: Correct Packer scripts, rebuild AMI, update terraform
- **Manual validation**: Always test AMI before setting as ASG default
- **Gradual rollout**: Use instance refresh with checkpoints enabled

## Cost Spike Investigation

### Symptoms
- Unexpected AWS bill increase
- ASG running at max capacity for extended period
- High data transfer costs

### Diagnosis Steps
1. Check ASG desired/actual capacity history (CloudWatch)
2. Review scaling activities for unexpected scale-outs
3. Check ALB request count trends (daily/weekly)
4. Review CloudWatch alarm history for false triggers

### Common Causes
- Alarm threshold too low (scaling out unnecessarily)
- Traffic attack or bot crawling
- Stuck scale-out (alarm not clearing)
- No scale-in policy or too conservative

### Remediation
- **Threshold tuning**: Increase CPU/RequestCount thresholds if normal traffic patterns changed
- **Bot protection**: Add WAF rules, rate limiting
- **Stuck scaling**: Check alarm evaluation logic, add scale-in policies
- **Scheduled scaling**: Use scheduled actions for predictable peaks

## Emergency Contacts

- **On-call Engineer**: [Contact info]
- **AWS Support**: [Case link]
- **Runbook Updates**: [GitHub repo link]

## Related Resources

- Architecture diagram: `docs/ARCHITECTURE.md`
- Terraform configs: `terraform/asg.tf`, `terraform/alb.tf`
- CloudWatch dashboard: [Link]
- Alarm definitions: Check `terraform/asg.tf` alarm resources
