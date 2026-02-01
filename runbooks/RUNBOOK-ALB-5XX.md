# Runbook: ALB/Target 5xx Spike

**Mục tiêu:** Xác định nhanh 5xx đến từ đâu (ALB vs app/targets), khoanh vùng thời điểm, và đưa ra hướng xử lý an toàn.

## 1) Triệu chứng
- ALB 5xx tăng (HTTPCode_ELB_5XX_Count) hoặc client báo lỗi 5xx.
- Có thể kèm latency tăng, request count tăng, hoặc target unhealthy.

## 2) Thu thập dữ liệu (ưu tiên theo thứ tự)

### Bước A — Baseline nhanh (khuyến nghị)
- Prompt: `Cho tôi baseline check toàn bộ hệ thống`
- Expected: trả về **Infrastructure + Alarms + Metrics + DynamoDB** và `overall_health`.

### Bước B — Metrics 15–30 phút
- Prompt: `Baseline metrics 15 phút gần đây: request count, target 5xx, target response time, healthy/unhealthy hosts.`
- Kiểm tra:
  - Requests tăng đột biến?
  - 5xx có spike theo phút?
  - Latency tăng cùng spike 5xx?
  - Healthy hosts giảm / Unhealthy hosts tăng?

### Bước C — Alarms
- Prompt: `Có alarm nào đang ở trạng thái ALARM không?` (hoặc lọc theo prefix)
- Nếu alarm ALARM → ghi lại tên alarm + thời điểm + metric liên quan.

### Bước D — Logs quanh thời điểm spike
- Prompt: `Query logs 20 phút gần đây xem có Exception/Error/Traceback hoặc status_code>=500 không.`
- Nếu cần “tập trung quanh spike”, dùng lookback rộng hơn và lọc mạnh hơn:
  - minutes=60 (khi spike không chắc)
  - Query ưu tiên JSON fields: `log_type=exception` hoặc `status_code >= 500` nếu log format hỗ trợ.

## 3) Phân loại nguyên nhân (decision tree)

### Case 1: 5xx tăng + latency tăng + targets vẫn healthy
**Khả năng cao:** backpressure / bottleneck app / dependency (DB, upstream), thread pool, GC, connection pool.
- Next checks:
  - Logs: timeout, slow query, upstream error
  - DynamoDB throttling / latency (nếu dùng)
  - CPU/Mem app (nếu có metric)

### Case 2: 5xx tăng + HealthyHostCount giảm / Unhealthy tăng
**Khả năng cao:** target unhealthy, health check fail, app crash, deployment lỗi.
- Next checks:
  - Snapshot ASG: instances lifecycle/health
  - Logs app startup/crash
  - Nếu vừa deploy: rollback/instance refresh plan

### Case 3: 5xx tăng + request count tăng mạnh
**Khả năng cao:** traffic spike, rate limiting, autoscaling chưa kịp.
- Next checks:
  - ASG desired/min/max có đủ?
  - Scale-out events gần đây?
  - WAF/rate limiting (nếu có)

## 4) Hành động giảm thiểu (an toàn)
- Nếu do target unhealthy và có đủ capacity: cân nhắc rolling replace an toàn (plan trước).
- Nếu do traffic spike: tăng desired capacity (nếu bạn có tool) hoặc scale policy (manual).
- Nếu do dependency: giảm load, bật caching, rollback feature.

## 5) Nếu cần rolling deploy/repair
- Prompt: `Plan instance refresh với min_healthy_percentage=90, cho tôi biết risks`
- Chỉ execute khi user confirm rõ ràng.

## 6) Kết quả đầu ra chuẩn khi báo cáo
- Thời gian spike (UTC/local)
- Metric: request/5xx/latency + healthy/unhealthy
- Logs: top 3 lỗi tiêu biểu
- Kết luận sơ bộ + next step
