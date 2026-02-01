# Runbook: Unhealthy Targets / Health Check Fail

**Mục tiêu:** Xác định vì sao target unhealthy và khôi phục service nhanh.

## 1) Triệu chứng
- Target Group có UnhealthyHostCount > 0
- ALB trả 5xx/503
- API health check fail/timeout

## 2) Thu thập dữ liệu

### Bước A — Snapshot infra
- Prompt: `Cho tôi xem snapshot hạ tầng hiện tại`
- Lấy:
  - Target group health_counts
  - ASG health_counts + lifecycle_counts
  - Instance refresh status

### Bước B — Metrics
- Prompt: `Lấy metrics ALB/TargetGroup 15 phút gần đây`
- Kiểm tra 5xx, latency, healthy/unhealthy trends

### Bước C — Logs
- Prompt: `Query logs 30 phút gần đây xem có error/exception hoặc crash không`
- Tập trung vào:
  - Startup errors
  - Health endpoint errors (/health)
  - MemoryError/OOM patterns (nếu có)

### Bước D — API health
- Prompt: `Check health các endpoint API`

## 3) Nguyên nhân thường gặp
- App process chết hoặc chưa start xong
- Health check path/port sai
- Security group/NACL chặn traffic health check
- Instance warmup quá ngắn (app cần lâu để warm)
- Deploy mới bị lỗi config/env

## 4) Hành động khắc phục (ưu tiên an toàn)

### Option A: Nếu chỉ 1 instance unhealthy và còn instance healthy
- Cân nhắc rolling replace instance lỗi:
  - Prompt: `Plan instance refresh với min_healthy_percentage=90, cho tôi biết risks`

### Option B: Nếu nhiều instance unhealthy
- Không execute refresh vội nếu risk cao.
- Tăng capacity tạm thời (nếu có) để giữ min healthy.

### Option C: Nếu do health check config
- Sửa health check path/port và redeploy (manual)

## 5) Tiêu chí phục hồi
- Target group: Unhealthy = 0
- API health endpoints trả 200
- 5xx trở về 0 trong window 15 phút
