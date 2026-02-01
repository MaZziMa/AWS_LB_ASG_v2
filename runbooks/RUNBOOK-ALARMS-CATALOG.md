# Runbook: Alarm Catalog & Response Rules

**Mục tiêu:** Chuẩn hóa cách đọc alarm và phản ứng tương ứng.

## 1) Cách kiểm tra nhanh
- Prompt: `Có alarm nào đang ở trạng thái ALARM không?`
- Nếu muốn lọc theo hệ thống: dùng prefix (ví dụ `course-management`).

## 2) Quy tắc phân loại mức độ

### P0 (Critical)
- Nhiều 5xx kéo dài, hoặc HealthyHostCount = 0
- API health fail trên nhiều endpoint
**Action:** ưu tiên RCA ngay, cân nhắc rollback/disable feature.

### P1 (High)
- 5xx tăng nhưng còn healthy targets
- Latency tăng mạnh kéo dài
**Action:** điều tra logs + dependency, chuẩn bị mitigation.

### P2 (Medium)
- INSUFFICIENT_DATA hoặc alarm flapping
**Action:** kiểm tra traffic; tăng window; xem cấu hình alarm.

## 3) Mapping nhanh (theo alarm thực tế hiện có)
> Dựa trên danh sách alarms hiện có trong môi trường hiện tại. Nếu về sau đổi tên, cập nhật lại bảng.

| Alarm pattern | Ý nghĩa | Check nhanh | Hướng xử lý |
|---|---|---|---|
| `CourseReg-High5xxErrors` | Target 5xx tăng (ALB/TG) | metrics + logs | RUNBOOK-ALB-5XX |
| `course-management-high-cpu-dev` | CPU cao (ASG/EC2) | snapshot + metrics | RUNBOOK-TIMEOUT-LATENCY (check backpressure/dependency) |
| `course-management-low-cpu-dev` | CPU thấp bất thường (có thể scale-in/ít traffic) | snapshot + metrics | Baseline check + xem scaling activities |
| `TargetTracking-course-management-asg-dev-AlarmHigh-*` | Target tracking scale-out trigger (CPU high) | snapshot + metrics | Baseline check + kiểm tra request/latency |
| `TargetTracking-course-management-asg-dev-AlarmLow-*` | Target tracking scale-in trigger (CPU low) | snapshot + metrics | Baseline check + xác nhận có phải giờ thấp điểm |
| `high-cpu-utilization` | CPU cao (generic) | snapshot + metrics | RUNBOOK-TIMEOUT-LATENCY |

## 4) Yêu cầu báo cáo khi alarm ALARM
- Alarm name + state
- Thời gian bắt đầu
- Metric liên quan (5xx/latency/healthy)
- Kết luận sơ bộ + next step
