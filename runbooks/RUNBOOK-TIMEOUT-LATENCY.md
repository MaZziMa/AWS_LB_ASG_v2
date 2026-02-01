# Runbook: Timeout / High Latency

**Mục tiêu:** Phân biệt latency do app/dependency hay do hạ tầng/targets; đưa ra bước xử lý.

## 1) Triệu chứng
- Client timeout / 504
- Latency target/ALB tăng
- Có thể request count không tăng nhưng latency vẫn tăng

## 2) Thu thập dữ liệu

### Bước A — Baseline check
- Prompt: `Cho tôi baseline check toàn bộ hệ thống`

### Bước B — Metrics window 15–60 phút
- Prompt: `Lấy metrics ALB/TargetGroup 30 phút gần đây` (hoặc 15/60 tùy)
- Nhìn các chỉ số:
  - TargetResponseTime/Latency có datapoints không?
  - 5xx có đi kèm latency không?
  - Healthy/Unhealthy có thay đổi không?

### Bước C — API health
- Prompt: `Check health các endpoint API`
- Nếu timeout:
  - Xác nhận ALB DNS đúng (API_BASE_URL trong Lambda env)
  - Có thể backend/app down hoặc security group/NACL issue

### Bước D — Logs
- Prompt: `Query logs 30 phút gần đây xem có timeout, slow request, Exception không`

### Bước E — DynamoDB
- Prompt: `Kiểm tra DynamoDB có bị throttle không?`

## 3) Phân loại nguyên nhân

### Case 1: Latency tăng + logs có timeout/upstream
**Khả năng:** dependency chậm (DB/third-party), connection pool cạn.
- Next steps:
  - Kiểm tra throttling (DynamoDB)
  - Giảm concurrency / rollout config

### Case 2: Latency tăng + HealthyHostCount giảm
**Khả năng:** targets mất health, health check fail.
- Next steps:
  - Snapshot infra để xem ASG health/lifecycle
  - Điều tra app crash / out-of-memory

### Case 3: API health timeout nhưng ALB vẫn active
**Khả năng:** app process down, routing/security issue, instance warmup chưa xong.
- Next steps:
  - Snapshot infra + scaling activities
  - Query logs của app/instance

## 4) Hành động giảm thiểu
- Nếu unhealthy targets: plan instance refresh (an toàn) hoặc rollback
- Nếu dependency: giảm load, tắt feature gây chậm, tăng capacity dependency

## 5) Ghi chú về “0 datapoints”
- Nếu metric latency/healthy/unhealthy trống:
  - Có thể do ít traffic trong window
  - Tăng window lên 60 phút
  - Tăng period_seconds nếu cần
