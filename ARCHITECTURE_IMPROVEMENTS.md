# Cải tiến Kiến trúc - Quick Wins

## 1. Cache Layer (Redis/ElastiCache)
```python
# Giảm 70% calls đến DynamoDB/CloudWatch
import redis
cache = redis.Redis(host='elasticache-endpoint')

@app.get("/api/ops/realtime/infra")
async def ops_realtime_infra():
    cached = cache.get("infra_snapshot")
    if cached:
        return json.loads(cached)
    
    snapshot = collect_infra_snapshot()
    cache.setex("infra_snapshot", 30, json.dumps(snapshot))  # 30s TTL
    return snapshot
```

**Impact:** Giảm latency từ 500ms → 50ms, giảm cost 40%

## 2. Async Processing (SQS + Background Workers)
```python
# Đẩy heavy tasks sang queue
@app.post("/api/ops/ask")
async def ask_ops_agent(query: AgentQuery):
    # Sync: Trả về ngay request_id
    request_id = str(uuid.uuid4())
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps({"request_id": request_id, "query": query.question})
    )
    return {"request_id": request_id, "status": "processing"}

# Client poll kết quả
@app.get("/api/ops/result/{request_id}")
async def get_result(request_id: str):
    result = cache.get(f"result:{request_id}")
    return {"status": "completed" if result else "processing", "result": result}
```

**Impact:** User không phải đợi, UX tốt hơn

## 3. Remove Duplicate Code
```python
# Tạo shared library cho cả EC2 và Lambda
# shared/infra_utils.py
def get_asg_status(asg_name: str) -> dict:
    """Shared function used by both EC2 app and Lambda"""
    asg = boto3.client('autoscaling')
    resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    return resp['AutoScalingGroups'][0]

# Deploy as Lambda Layer + pip package
```

**Impact:** Dễ maintain, ít bug hơn

## 4. API Gateway cho Lambda (thay vì EC2 gọi Lambda)
```
User → ALB → EC2 (FastAPI)
User → API Gateway → Lambda (Bedrock Actions)  # Direct call
```

**Impact:** Giảm 1 hop, latency giảm 200-300ms

## 5. Bedrock Streaming Response
```python
@app.post("/api/ops/ask")
async def ask_ops_agent(query: AgentQuery):
    def generate():
        for chunk in invoke_ops_agent_stream(query.question):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Impact:** User thấy response ngay, không phải đợi 5-10s

## 6. Monitoring & Alerting
```python
# CloudWatch Custom Metrics
cloudwatch = boto3.client('cloudwatch')

@app.middleware("http")
async def track_bedrock_latency(request: Request, call_next):
    if "/api/ops/ask" in request.url.path:
        start = time.time()
        response = await call_next(request)
        latency = time.time() - start
        
        cloudwatch.put_metric_data(
            Namespace='CourseApp/Bedrock',
            MetricData=[{
                'MetricName': 'BedrockLatency',
                'Value': latency,
                'Unit': 'Seconds'
            }]
        )
        return response
```

**Impact:** Phát hiện bottleneck nhanh

## 7. Cost Optimization
- **Spot Instances cho ASG**: Giảm 70% chi phí EC2
- **DynamoDB On-Demand → Provisioned**: Nếu traffic ổn định
- **S3 Intelligent-Tiering**: Cho Bedrock KB documents
- **Lambda Reserved Concurrency**: Nếu traffic cao

## Migration Path (Zero Downtime)

### Phase 1: Quick Wins (1 tuần)
1. Add Redis cache
2. Add CloudWatch metrics
3. Remove duplicate code

### Phase 2: Async (2 tuần)
1. Add SQS queue
2. Implement background workers
3. Add polling endpoint

### Phase 3: Serverless Migration (1 tháng)
1. Deploy Lambda version song song
2. Route 10% traffic → Lambda (canary)
3. Monitor metrics
4. Gradually increase to 100%
5. Decommission EC2

## Recommended: Start with Option 2 (ECS Fargate)

**Why?**
- Giữ nguyên FastAPI code
- Chi phí giảm 40-50%
- Scale tốt hơn
- Dễ migrate từ EC2

**Migration:**
```bash
# 1. Containerize (đã có Dockerfile)
docker build -t course-app .

# 2. Push to ECR
aws ecr create-repository --repository-name course-app
docker push <ecr-url>

# 3. Update Terraform
# terraform/ecs.tf (thay thế asg.tf)
resource "aws_ecs_cluster" "main" {
  name = "course-management"
}

resource "aws_ecs_service" "app" {
  name            = "course-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "course-app"
    container_port   = 8000
  }
}

# 4. Deploy
terraform apply
```

**Result:** Same functionality, 50% cheaper, 10x faster deployment
