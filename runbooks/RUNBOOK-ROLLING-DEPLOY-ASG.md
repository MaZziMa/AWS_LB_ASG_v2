# Runbook: Rolling Deploy / ASG Instance Refresh (Plan → Confirm → Execute)

**Mục tiêu:** Triển khai/repair an toàn trên ASG bằng Instance Refresh.

## 0) Quy tắc an toàn
- **Luôn plan trước** bằng `plan_instance_refresh`.
- **Chỉ execute khi có xác nhận rõ ràng** từ người vận hành (ĐỒNG Ý/YES).
- Nếu ASG chỉ có 1 instance → refresh sẽ gây downtime ngắn.

## 1) Pre-check
- Prompt: `Cho tôi xem snapshot hạ tầng hiện tại`
- Kiểm tra:
  - desired capacity (>=2 khuyến nghị)
  - target group healthy = desired
  - có instance refresh đang chạy không

## 2) Plan
- Prompt: `Plan instance refresh với min_healthy_percentage=90, cho tôi biết risks`
- Đọc các trường:
  - validation.ongoing_refresh: có refresh đang chạy?
  - validation.asg.desired/healthy_count
  - validation.impact: max_replace_at_once, estimated_waves, estimated_duration
  - risks: LOW/MEDIUM/HIGH (hoặc list)

## 3) Decision
- Nếu risks cao:
  - giảm tốc deploy (tăng instance_warmup)
  - tăng desired capacity trước (manual)
  - hoãn deploy nếu đang incident

## 4) Execute (chỉ khi user confirm)
- Prompt xác nhận: `ĐỒNG Ý, execute now`
- Tool: `execute_instance_refresh`

## 5) Verify sau deploy
- Baseline:
  - Prompt: `Cho tôi baseline check toàn bộ hệ thống`
- API:
  - Prompt: `Check health các endpoint API`
- Logs:
  - Prompt: `Query logs 15 phút gần đây xem có Exception hoặc Error không`

## 6) Rollback (nếu cần)
- Nếu deploy gây lỗi:
  - Dừng rollout thủ công (tùy cơ chế)
  - Deploy lại phiên bản trước (manual)
  - Thực hiện refresh khác nếu cần (plan trước)

## 7) Ghi nhận
- Thời gian bắt đầu/kết thúc refresh
- 5xx/latency trước và sau
- Số instance replaced
