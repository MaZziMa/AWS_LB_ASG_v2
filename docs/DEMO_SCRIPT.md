# 🎬 Kịch Bản Demo: AI DevOps Assistant (Bedrock Agents + Action Groups)

## 📋 Tổng Quan Demo

Demo này trình bày khả năng AI tự động troubleshoot hệ thống AWS bằng **Bedrock Agent + Action Groups** (Agent tự chọn tool):
- **Real-time Infrastructure Monitoring**
- **DynamoDB Performance Analysis**  
- **Auto Scaling Group Management**
- **API Health & Pagination Check**
- **Root-cause hướng dẫn cho lỗi 5xx** (dựa trên trace/log/metrics nếu có)

**Thời gian demo:** ~15–20 phút  
**Môi trường:** Course Management System (Dev)

**Điều kiện trước demo (rất quan trọng):**
- Agent đã được **Prepare** và bạn đang test đúng **Alias/Version** mới nhất.
- Action group `devops-operations` đã attach Lambda `ops-agent-actions` và schema OpenAPI.
- Nếu demo API checks (`check_api_health`/`check_api_pagination`): `API_BASE_URL` phải là URL Lambda truy cập được (thường là ALB DNS), không dùng `localhost`.

---

## 🎯 Scenario 0 (30s): Chứng minh Agent đang gọi Tool (Trace)

### Prompt 0.1 - Tool invocation smoke test
```
Kiểm tra infra hiện tại
```
**Bạn trình bày:** Mở **Show trace** → xác nhận có bước gọi tool `get_infrastructure_snapshot` và output JSON có `timestamp` gần thời điểm hiện tại.

---

## 🎯 Scenario 1: Health Check Toàn Diện (Infra)

### Prompt 1.1 - Infrastructure Overview
```
Kiểm tra tình trạng infrastructure hiện tại
```
**Kết quả:** Agent gọi tool `get_infrastructure_snapshot` và tóm tắt ASG/TG/ALB.

### Prompt 1.2 - Thêm đánh giá & khuyến nghị
```
Kiểm tra infra hiện tại và cho tôi biết có thể cải thiện gì không?
```
**Kết quả:** Agent vẫn gọi tool, sau đó đưa khuyến nghị (ví dụ: health counts, scaling events, instance refresh).

---

## 🎯 Scenario 2: DynamoDB Analysis (Throttling / Capacity)

### Prompt 2.1 - Metrics Overview
```
Kiểm tra DynamoDB metrics
```

**Bạn trình bày:** Mở trace → tool `get_dynamodb_metrics`.

### Prompt 2.2 - AI Analysis
```
Phân tích DynamoDB metrics và đề xuất tối ưu
```
**Kết quả:** Tóm tắt consumed capacity/throttle + đề xuất hành động.

### Prompt 2.3 - Throttling focused
```
Kiểm tra DynamoDB có bị throttling trong 10 phút gần đây không?
```
**Kết quả:** Agent tập trung vào `ReadThrottleEvents/WriteThrottleEvents/ThrottledRequests`.

---

## 🎯 Scenario 3: API Health & Pagination (App Troubleshooting)

### Prompt 3.1 - Check All Endpoints
```
Kiểm tra API health
```
**Kết quả:** Agent gọi `check_api_health` và báo status/latency theo endpoint.

### Prompt 3.2 - Check Pagination
```
Kiểm tra backend đã thực hiện phân trang cho API courses chưa
```
**Kết quả:** Agent gọi `check_api_pagination` và kết luận kiểu phân trang (page/limit, offset/limit...).

### Prompt 3.3 - Check với AI Analysis  
```
Kiểm tra API pagination và đề xuất cải tiến
```
**Kết quả:** Đề xuất chuẩn hoá response shape (total, page, limit) và error handling.

---

## 🎯 Scenario 4: Deployment Operations (ASG Instance Refresh)

---

## 🎯 Scenario 4: Deployment Operations

### Prompt 4.1 - Plan Instance Refresh (Safe)
```
Lên kế hoạch instance refresh cho ASG nhưng chưa thực thi
```

**Bạn trình bày:** Nhấn mạnh an toàn: plan trước, không gây gián đoạn.

### Prompt 4.2 - Execute (với approval)
```
Tôi xác nhận: hãy thực thi instance refresh cho ASG course-management-asg-dev
```

**Bạn trình bày:** Agent chỉ được phép gọi `execute_instance_refresh` khi có xác nhận rõ ràng.

---

## 🎯 Scenario 5: “Vì sao bị 500?” (RCA playbook)

### Prompt 5.1 - Triaging khi người dùng báo lỗi
```
Người dùng báo API /api/courses bị 500. Bạn cần kiểm tra gì trước?
```
**Kết quả:** Agent đưa checklist: xác định scope, thời điểm, tần suất, request id, kiểm tra target health, latency, dependency.

### Prompt 5.2 - Đo nhanh từ bên ngoài (nếu có base_url)
```
Kiểm tra API health và cho biết endpoint nào có dấu hiệu lỗi/timeout
```
**Kết quả:** Dựa trên `check_api_health` để khoanh vùng.

> Ghi chú: Để “kết luận nguyên nhân 500” một cách chắc chắn, cần tích hợp thêm tools đọc CloudWatch Logs/X-Ray (có thể làm phase tiếp theo).

---

## 📝 Prompt Cheat Sheet

| Mục đích | Prompt |
|----------|--------|
| Infra snapshot | `Kiểm tra infra hiện tại` |
| Infra + khuyến nghị | `Kiểm tra infra hiện tại và cho tôi biết có thể cải thiện gì không?` |
| DynamoDB metrics | `Kiểm tra DynamoDB metrics` |
| Throttling | `Kiểm tra DynamoDB có bị throttling không?` |
| API health | `Kiểm tra API health` |
| Pagination | `Kiểm tra backend đã thực hiện phân trang cho API courses chưa` |
| Plan refresh | `Lên kế hoạch instance refresh cho ASG nhưng chưa thực thi` |
| Execute refresh | `Tôi xác nhận: hãy thực thi instance refresh cho ASG ...` |

---

## ⚙️ Cấu Hình

**File `.env` (backend/local dev):**
```env
USE_BEDROCK=true
AWS_REGION=us-east-1
OPS_ASG_NAME=course-management-asg-dev
OPS_DDB_TABLES=course-management-courses-dev,course-management-enrollments-dev,course-management-students-dev
API_BASE_URL=http://localhost:8000
```

**Lambda env (Action Groups):**
- `API_BASE_URL` nên là ALB URL (ví dụ `https://<alb-dns>`) để Lambda gọi được.
- Không dùng `http://localhost:8000` trong Lambda.

---

*Last updated: December 22, 2025*
