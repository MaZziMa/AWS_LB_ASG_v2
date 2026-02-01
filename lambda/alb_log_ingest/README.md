# ALB Access Logs Ingest Lambda

Lambda này đọc file `.log.gz` từ S3 (ALB access logs) và đẩy vào CloudWatch Logs để AIOps có thể query.

## Kiến trúc

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ALB ACCESS LOGS FLOW                        │
└─────────────────────────────────────────────────────────────────────┘

   👤 User Request
    │
    ▼
┌─────────────────────┐
│        ALB          │
│  (Load Balancer)    │
└──────────┬──────────┘
           │
           │  ❶ Mỗi 5 phút, ALB ghi logs
           │
           ▼
┌─────────────────────┐
│    S3 Bucket        │
│  .log.gz (gzip)     │◄─── File nén chứa access logs
└──────────┬──────────┘
           │
           │  ❷ S3 Event trigger
           │
           ▼
┌─────────────────────┐
│  Lambda Ingest      │
│  alb-log-ingest     │◄─── Đọc gzip, parse, transform
└──────────┬──────────┘
           │
           │  ❸ Put log events (JSON format)
           │
           ▼
┌─────────────────────┐
│  CloudWatch Logs    │
│  /aws/alb/...       │◄─── AIOps query được!
└──────────┬──────────┘
           │
           │  ❹ get_latest_http_5xx query
           │
           ▼
┌─────────────────────┐
│  Bedrock Agent      │
│  AIOps Tools        │
└─────────────────────┘
```

## ALB Log Format → JSON

**Input (ALB raw log):**
```
http 2025-12-25T10:30:00.123456Z app/course-management-alb-dev/abc123 
10.0.1.50:54321 10.0.2.100:8000 0.001 0.050 0.000 502 - 
123 456 "GET /api/courses HTTP/1.1" "curl/7.68.0" - - 
arn:aws:elasticloadbalancing:... "Root=1-abc-def" "example.com" ...
```

**Output (JSON in CloudWatch):**
```json
{
  "timestamp": "2025-12-25T10:30:00.123456Z",
  "log_type": "alb_access",
  "status_code": 502,
  "elb_status_code": 502,
  "target_status_code": null,
  "method": "GET",
  "path": "/api/courses",
  "client_ip": "10.0.1.50",
  "target_ip": "10.0.2.100",
  "latency_ms": 51.0,
  "error_reason": "TargetConnectionError",
  "trace_id": "Root=1-abc-def"
}
```

## Các error codes từ ALB

| Status | Error Reason | Nguyên nhân |
|--------|--------------|-------------|
| **502** | `TargetConnectionError` | Target (EC2) không phản hồi |
| **502** | `TargetResponseMalformed` | Response không hợp lệ |
| **503** | `TargetNotAvailable` | Không có target healthy |
| **504** | `TargetTimeout` | Target timeout (>60s mặc định) |
| **460** | - | Client đóng connection |
| **463** | - | X-Forwarded-For header không hợp lệ |

## Deploy

```powershell
cd terraform
terraform init
terraform apply
```

## Cập nhật OPS_LOG_GROUPS

Sau khi deploy, thêm ALB log group vào Lambda `ops-agent-actions`:

```powershell
# Lấy tên log group mới
$ALB_LOG_GROUP = terraform output -raw alb_logs_cloudwatch_group
# Output: /aws/alb/course-management-dev

# Cập nhật terraform.tfvars trong lambda/ops_agent_actions/
# Thêm vào ops_log_groups:
# ops_log_groups = "/aws/ec2/course-management-dev,/aws/imagebuilder/course-management-dev-recipe,/aws/alb/course-management-dev"
```

## Test

1. **Tạo traffic qua ALB:**
   ```powershell
   curl http://course-management-alb-dev-....elb.amazonaws.com/api/courses
   ```

2. **Đợi 5 phút** (ALB logs batch mỗi 5 phút)

3. **Kiểm tra CloudWatch Logs:**
   ```powershell
   aws logs filter-log-events `
     --log-group-name "/aws/alb/course-management-dev" `
     --filter-pattern "status_code" `
     --limit 5
   ```

4. **Test AIOps:**
   ```
   Hỏi: "Có lỗi 502/503 nào từ ALB không?"
   ```

## Lưu ý

- ALB logs có độ trễ ~5 phút (batch interval)
- File `.log.gz` được S3 lifecycle tự động xóa sau 7 ngày (dev) / 30 ngày (prod)
- Lambda timeout: 60s, memory: 256MB
- Mỗi file log thường chứa 1000-10000 records
