# Course Management System - Architecture Context

## System Overview
The Course Management System is a FastAPI-based web application deployed on AWS with high availability and auto-scaling capabilities. The system provides REST APIs for managing courses, students, and enrollments with DynamoDB as the backend database.

## Infrastructure Components

### Load Balancer (ALB)
- **Name**: course-management-alb-dev
- **Type**: Application Load Balancer (Layer 7)
- **Scheme**: Internet-facing
- **Region**: us-east-1
- **DNS**: course-management-alb-dev-1530526851.us-east-1.elb.amazonaws.com
- **Purpose**: Distributes incoming HTTP/HTTPS traffic across multiple EC2 instances

**Key Features**:
- Health checks on `/health` endpoint (30s interval, 2 consecutive successes, 5 failures threshold)
- Connection draining (300s)
- Access logs enabled to S3 for monitoring
- Target group: course-management-tg

### Auto Scaling Group (ASG)
- **Name**: course-management-asg-dev
- **Min Capacity**: 1 instance
- **Max Capacity**: 4 instances
- **Desired Capacity**: 2 instances (typical)
- **Health Check**: ELB + EC2 health checks
- **Health Check Grace Period**: 300 seconds

**Scaling Policies**:
1. **Scale Up**: When average CPU > 70% for 2 consecutive periods (300s each)
   - Add 1 instance
   - Cooldown: 300s
   
2. **Scale Down**: When average CPU < 30% for 10 consecutive periods (300s each)
   - Remove 1 instance
   - Cooldown: 600s

### EC2 Instances
- **Instance Type**: t3.micro (2 vCPU, 1 GiB RAM)
- **AMI**: Amazon Linux 2023
- **Application**: FastAPI + Uvicorn (port 8000)
- **User Data**: Installs Python 3.11, dependencies, starts app via systemd

### DynamoDB Tables
- **courses**: Stores course information (course_id, title, instructor, price, etc.)
- **students**: Stores student profiles (student_id, name, email, phone)
- **enrollments**: Tracks course enrollments (enrollment_id, student_id, course_id, progress)

## Traffic Flow

```
Internet → ALB (Port 80/443)
  ↓
Target Group Health Check (/health)
  ↓
EC2 Instances (Auto Scaling Group)
  ↓ Port 8000
FastAPI Application
  ↓
DynamoDB Tables (courses, students, enrollments)
```

## Scaling Behavior

### Normal Operation
- 2 instances running behind ALB
- CPU utilization: 20-40%
- Response time: <100ms (P95)
- Healthy targets: 2/2

### High Load Scenario
1. Traffic increases → CPU > 70%
2. CloudWatch alarm triggers → ASG scales up
3. New instance launches → 5 min startup time
4. Instance passes health checks → Added to target group
5. ALB distributes traffic to 3+ instances
6. CPU drops below 70% → Stable state

### Scale Down Scenario
1. Traffic decreases → CPU < 30% for 50 minutes
2. ASG scales down → Removes 1 instance
3. Connection draining (300s) → Graceful shutdown
4. Instance terminates → Capacity returns to 2

## Common Failure Patterns

### 1. Failed Health Checks
**Symptoms**: Targets marked unhealthy, 502 Bad Gateway errors
**Causes**:
- Application crash (OOM, unhandled exception)
- Slow /health endpoint response (>5s)
- Security group misconfiguration
- Instance networking issues

### 2. Scaling Lag
**Symptoms**: High latency despite scale-up, slow response times
**Causes**:
- 5-minute EC2 launch time
- Application startup time (pip install, model loading)
- Health check grace period (300s)
- Insufficient max capacity

### 3. DynamoDB Throttling
**Symptoms**: 500 errors, ProvisionedThroughputExceededException
**Causes**:
- Scan operations on large tables
- Burst traffic exceeding provisioned capacity
- Missing GSI for query patterns

### 4. 5xx Errors
**Symptoms**: HTTP 500/502/503/504 responses
**Causes**:
- Application exceptions (unhandled errors)
- Target unavailability during deployment
- ALB timeout (60s) for slow endpoints
- DynamoDB connection failures

## Deployment Patterns

### Blue/Green Deployment
1. Create new Launch Template version with updated AMI/code
2. Update ASG to use new Launch Template
3. Trigger instance refresh (50% replacement at a time)
4. Monitor health checks and error rates
5. Rollback if error rate > 5%

### Rolling Update
1. Update Launch Template
2. Set ASG min capacity to desired * 2
3. Terminate old instances one by one
4. Wait for new instances to pass health checks
5. Restore original min capacity

## Monitoring & Observability

### Key Metrics
- **ALB**: RequestCount, TargetResponseTime, HTTPCode_Target_5XX_Count, UnHealthyHostCount
- **ASG**: GroupDesiredCapacity, GroupInServiceInstances, GroupTerminatingInstances
- **EC2**: CPUUtilization, NetworkIn, NetworkOut, StatusCheckFailed
- **DynamoDB**: ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, UserErrors

### Alarms
- High 5xx error rate (>5% for 5 minutes)
- Unhealthy targets (>0 for 2 minutes)
- High CPU (>80% for 10 minutes)
- DynamoDB throttling (>10 throttled requests)

### Logging
- **ALB Access Logs**: S3 bucket (course-management-bedrock-kb-dev/bedrock/logs/alb/)
- **Application Logs**: CloudWatch Logs (if configured)
- **ASG Activity History**: via describe-scaling-activities API

## Security

### IAM Roles
- **EC2 Instance Role**: AmazonDynamoDBFullAccess, CloudWatchAgentServerPolicy
- **ALB Service Role**: Managed by AWS (automatic S3 log delivery)

### Security Groups
- **ALB SG**: Inbound 80/443 from 0.0.0.0/0, Outbound to Target SG port 8000
- **Instance SG**: Inbound 8000 from ALB SG, SSH 22 from bastion (optional)

### Network
- **VPC**: Default VPC or custom VPC with public subnets
- **Subnets**: Multi-AZ (us-east-1a, us-east-1b for high availability)

## Cost Optimization

### Typical Monthly Cost (us-east-1)
- ALB: ~$22/month (750 LCU-hours free tier)
- EC2 (2x t3.micro): ~$15/month
- DynamoDB (on-demand): ~$5-20/month (usage-dependent)
- Data Transfer: ~$5-10/month
- **Total**: ~$47-67/month

### Optimization Tips
- Use Savings Plans for EC2 (up to 72% discount)
- Enable DynamoDB auto-scaling
- Review ALB idle timeout settings
- Archive old ALB logs to Glacier after 90 days

## Disaster Recovery

### RTO/RPO
- **Recovery Time Objective (RTO)**: 15 minutes (launch new ASG + health checks)
- **Recovery Point Objective (RPO)**: <1 minute (DynamoDB continuous backups)

### Backup Strategy
- DynamoDB Point-in-Time Recovery enabled
- Launch Template versioning
- AMI snapshots for EC2 (weekly)

## References
- ALB Documentation: https://docs.aws.amazon.com/elasticloadbalancing/
- ASG Best Practices: https://docs.aws.amazon.com/autoscaling/ec2/userguide/
- DynamoDB Best Practices: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/
