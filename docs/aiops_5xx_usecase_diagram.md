# Use Case Diagram: AIOps 5xx Error Detection & Root Cause Analysis

## 1. Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AIOps System Architecture                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────┐                                                                 │
│    │  DevOps  │                                                                 │
│    │ Engineer │                                                                 │
│    └────┬─────┘                                                                 │
│         │                                                                       │
│         │ "Kiểm tra lỗi 5xx trong hệ thống"                                     │
│         ▼                                                                       │
│    ┌─────────────────────────────────────────┐                                  │
│    │         Amazon Bedrock Agent            │                                  │
│    │  ┌─────────────────────────────────┐    │                                  │
│    │  │   Claude AI (Foundation Model)  │    │                                  │
│    │  │   - Hiểu ngữ cảnh câu hỏi       │    │                                  │
│    │  │   - Chọn tool phù hợp           │    │                                  │
│    │  │   - Tổng hợp & giải thích       │    │                                  │
│    │  └─────────────────────────────────┘    │                                  │
│    └────────────────┬────────────────────────┘                                  │
│                     │                                                           │
│                     │ Invoke Action Group                                       │
│                     ▼                                                           │
│    ┌─────────────────────────────────────────┐                                  │
│    │      Lambda: ops-agent-actions          │                                  │
│    │  ┌─────────────────────────────────┐    │                                  │
│    │  │ get_5xx_root_cause_analysis()   │    │                                  │
│    │  │ - Query CloudWatch Logs         │    │                                  │
│    │  │ - Analyze error patterns        │    │                                  │
│    │  │ - Correlate infrastructure      │    │                                  │
│    │  │ - Generate recommendations      │    │                                  │
│    │  └─────────────────────────────────┘    │                                  │
│    └────────────────┬────────────────────────┘                                  │
│                     │                                                           │
│         ┌───────────┴───────────┐                                               │
│         ▼                       ▼                                               │
│    ┌──────────┐           ┌──────────┐                                          │
│    │CloudWatch│           │CloudWatch│                                          │
│    │  Logs    │           │ Metrics  │                                          │
│    │ (EC2,ALB)│           │(CPU,Mem) │                                          │
│    └──────────┘           └──────────┘                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Use Case Diagram (UML)

```
                           ┌─────────────────────────────────────────────────┐
                           │              AIOps System                        │
                           │                                                  │
                           │  ┌─────────────────────────────────────────┐    │
                           │  │                                         │    │
   ┌──────────┐            │  │    (UC1) Tìm lỗi HTTP 5xx              │    │
   │          │   ask      │  │    ─────────────────────               │    │
   │  DevOps  │───────────►│  │    Actor: DevOps                       │    │
   │ Engineer │            │  │    Mục đích: Tìm các lỗi server        │    │
   │          │◄───────────│  │    trong khoảng thời gian              │    │
   └──────────┘   response │  │                                         │    │
                           │  └───────────────┬─────────────────────────┘    │
                           │                  │ <<include>>                   │
                           │                  ▼                               │
                           │  ┌─────────────────────────────────────────┐    │
                           │  │    (UC2) Phân tích nguyên nhân gốc      │    │
                           │  │    ────────────────────────────         │    │
                           │  │    - Phân loại lỗi (502/503/504)        │    │
                           │  │    - Xác định thời điểm lỗi xảy ra      │    │
                           │  │    - Liên kết với infrastructure        │    │
                           │  └───────────────┬─────────────────────────┘    │
                           │                  │ <<include>>                   │
                           │         ┌────────┴────────┐                      │
                           │         ▼                 ▼                      │
                           │  ┌────────────┐    ┌────────────────┐           │
                           │  │(UC3) Query │    │(UC4) Check     │           │
                           │  │CloudWatch  │    │Infrastructure  │           │
                           │  │Logs        │    │Metrics         │           │
                           │  └────────────┘    └────────────────┘           │
                           │                                                  │
                           │                  │ <<include>>                   │
                           │                  ▼                               │
                           │  ┌─────────────────────────────────────────┐    │
                           │  │    (UC5) Tạo báo cáo & đề xuất          │    │
                           │  │    ────────────────────────             │    │
                           │  │    - Tóm tắt lỗi bằng tiếng Việt        │    │
                           │  │    - Đề xuất cách khắc phục             │    │
                           │  │    - Cảnh báo nếu nghiêm trọng          │    │
                           │  └─────────────────────────────────────────┘    │
                           │                                                  │
                           └─────────────────────────────────────────────────┘
```

## 3. Sequence Diagram - Luồng xử lý chi tiết

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌───────────┐     ┌───────────┐
│ DevOps  │     │Bedrock Agent │     │   Lambda    │     │CloudWatch │     │CloudWatch │
│Engineer │     │  (Claude)    │     │ops-agent-   │     │   Logs    │     │  Metrics  │
└────┬────┘     └──────┬───────┘     │  actions    │     └─────┬─────┘     └─────┬─────┘
     │                 │             └──────┬──────┘           │                 │
     │ 1. "Kiểm tra    │                    │                  │                 │
     │    lỗi 5xx"     │                    │                  │                 │
     │────────────────►│                    │                  │                 │
     │                 │                    │                  │                 │
     │                 │ 2. Phân tích intent│                  │                 │
     │                 │    Chọn tool:      │                  │                 │
     │                 │    get_5xx_root_   │                  │                 │
     │                 │    cause_analysis  │                  │                 │
     │                 │                    │                  │                 │
     │                 │ 3. Invoke Lambda   │                  │                 │
     │                 │───────────────────►│                  │                 │
     │                 │    {time_range:    │                  │                 │
     │                 │     "1h"}          │                  │                 │
     │                 │                    │                  │                 │
     │                 │                    │ 4. Query 5xx     │                 │
     │                 │                    │────────────────► │                 │
     │                 │                    │ filter:          │                 │
     │                 │                    │ status_code~5[0-9]{2}              │
     │                 │                    │                  │                 │
     │                 │                    │ 5. Return logs   │                 │
     │                 │                    │◄────────────────│                 │
     │                 │                    │ [{status:504,    │                 │
     │                 │                    │   path:/api/...}]│                 │
     │                 │                    │                  │                 │
     │                 │                    │ 6. Get metrics   │                 │
     │                 │                    │─────────────────────────────────► │
     │                 │                    │ CPUUtilization,  │                 │
     │                 │                    │ MemoryUtilization│                 │
     │                 │                    │                  │                 │
     │                 │                    │ 7. Return metrics│                 │
     │                 │                    │◄─────────────────────────────────│
     │                 │                    │                  │                 │
     │                 │                    │ 8. Analyze &     │                 │
     │                 │                    │    Correlate     │                 │
     │                 │                    │    ┌──────────┐  │                 │
     │                 │                    │    │- Group by│  │                 │
     │                 │                    │    │  status  │  │                 │
     │                 │                    │    │- Check   │  │                 │
     │                 │                    │    │  CPU/Mem │  │                 │
     │                 │                    │    │- Find    │  │                 │
     │                 │                    │    │  pattern │  │                 │
     │                 │                    │    └──────────┘  │                 │
     │                 │                    │                  │                 │
     │                 │ 9. Return analysis │                  │                 │
     │                 │◄───────────────────│                  │                 │
     │                 │ {summary, errors,  │                  │                 │
     │                 │  root_cause,       │                  │                 │
     │                 │  recommendations}  │                  │                 │
     │                 │                    │                  │                 │
     │                 │ 10. Tổng hợp &     │                  │                 │
     │                 │     format response│                  │                 │
     │                 │                    │                  │                 │
     │ 11. Trả lời     │                    │                  │                 │
     │     tiếng Việt  │                    │                  │                 │
     │◄────────────────│                    │                  │                 │
     │ "Phát hiện 5    │                    │                  │                 │
     │  lỗi 504 do     │                    │                  │                 │
     │  timeout..."    │                    │                  │                 │
     │                 │                    │                  │                 │
```

## 4. Chi tiết các Use Case

### UC1: Tìm lỗi HTTP 5xx

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | DevOps Engineer |
| **Mục đích** | Phát hiện các lỗi server (500, 502, 503, 504) trong hệ thống |
| **Precondition** | - AIOps Agent đã được deploy và configured<br>- CloudWatch Logs đang thu thập logs từ EC2 và ALB |
| **Trigger** | DevOps hỏi câu hỏi liên quan đến lỗi 5xx |
| **Main Flow** | 1. DevOps đặt câu hỏi (VD: "Có lỗi 5xx nào không?")<br>2. AI phân tích intent và chọn tool phù hợp<br>3. Thực hiện UC2-UC5<br>4. Trả kết quả cho DevOps |
| **Postcondition** | DevOps nhận được báo cáo chi tiết về lỗi 5xx |

### UC2: Phân tích nguyên nhân gốc

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | System (Lambda function) |
| **Mục đích** | Xác định nguyên nhân gốc của lỗi 5xx |
| **Input** | Danh sách lỗi 5xx từ CloudWatch Logs |
| **Process** | - Phân loại theo status code (502/503/504)<br>- Phân tích error_reason từ ALB<br>- Xác định endpoint bị ảnh hưởng nhiều nhất<br>- Tính toán tần suất và thời điểm lỗi |
| **Output** | Root cause analysis với confidence level |

### UC3: Query CloudWatch Logs

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | System (Lambda function) |
| **Log Groups** | - `/aws/ec2/course-management-dev` (Application logs)<br>- `/aws/alb/course-management-dev` (ALB access logs) |
| **Query Pattern** | `filter @message like /status_code.*5[0-9]{2}/` |
| **Time Range** | Configurable: 15m, 1h, 6h, 24h, 7d |

### UC4: Check Infrastructure Metrics

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | System (Lambda function) |
| **Metrics Checked** | - CPUUtilization<br>- MemoryUtilization (via CloudWatch Agent)<br>- NetworkIn/Out<br>- DiskReadOps/DiskWriteOps |
| **Purpose** | Correlate errors with resource exhaustion |

### UC5: Tạo báo cáo & đề xuất

| Thuộc tính | Mô tả |
|------------|-------|
| **Actor** | System (Lambda function + Claude AI) |
| **Output Format** | Vietnamese language report |
| **Components** | - **Tóm tắt**: Số lượng lỗi, loại lỗi, severity<br>- **Chi tiết**: Timeline, affected endpoints<br>- **Nguyên nhân**: Root cause với giải thích<br>- **Khuyến nghị**: Actionable recommendations |

## 5. Ví dụ Input/Output

### Input (DevOps hỏi)
```
"Kiểm tra xem trong 1 giờ qua có lỗi 5xx nào không?"
```

### Output (AIOps trả lời)
```
📊 BÁO CÁO LỖI 5XX - 1 GIỜ QUA

🔴 TỔNG QUAN:
- Tổng số lỗi: 8
- Loại lỗi: 504 Gateway Timeout (8)
- Mức độ: TRUNG BÌNH

📋 CHI TIẾT LỖI:
┌─────────────┬────────────────────────┬─────────────┐
│ Thời gian   │ Endpoint               │ Latency     │
├─────────────┼────────────────────────┼─────────────┤
│ 14:23:15    │ GET /api/courses       │ 60.2s       │
│ 14:25:33    │ GET /api/courses       │ 60.1s       │
│ 14:28:41    │ POST /api/enrollments  │ 60.0s       │
└─────────────┴────────────────────────┴─────────────┘

🔍 NGUYÊN NHÂN GỐC:
- error_reason: LambdaInvalidResponse (từ ALB)
- Backend xử lý quá 60 giây (ALB timeout mặc định)
- CPU tại thời điểm lỗi: 78% (cao)

💡 KHUYẾN NGHỊ:
1. Tăng timeout của ALB Target Group (hiện tại: 60s)
2. Optimize /api/courses endpoint - query database chậm
3. Xem xét scale out thêm instance nếu CPU > 70%
4. Thêm caching cho API courses
```

## 6. Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                 AWS Cloud                                     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Amazon Bedrock                                   │ │
│  │  ┌───────────────────┐    ┌──────────────────────────────────────────┐  │ │
│  │  │   Agent           │    │        Action Group                       │  │ │
│  │  │  (CGWF5H93V2)     │───►│  ┌─────────────────────────────────────┐  │  │ │
│  │  │                   │    │  │     OpenAPI Schema                   │  │  │ │
│  │  │  - Claude 3.5     │    │  │  ┌─────────────────────────────────┐ │  │  │ │
│  │  │  - Vietnamese     │    │  │  │ /get_5xx_root_cause_analysis   │ │  │  │ │
│  │  │    prompts        │    │  │  │ /get_ec2_status                │ │  │  │ │
│  │  │                   │    │  │  │ /get_alb_target_health         │ │  │  │ │
│  │  └───────────────────┘    │  │  │ /get_asg_status                │ │  │  │ │
│  │                           │  │  │ /search_logs                   │ │  │  │ │
│  │                           │  │  │ ...                            │ │  │  │ │
│  │                           │  │  └─────────────────────────────────┘ │  │  │ │
│  │                           │  └─────────────────────────────────────┘  │  │ │
│  │                           └──────────────────┬───────────────────────┘  │ │
│  └──────────────────────────────────────────────┼──────────────────────────┘ │
│                                                 │                            │
│                                                 ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         AWS Lambda                                       │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │                  ops-agent-actions                                 │  │ │
│  │  │                                                                    │  │ │
│  │  │  ┌────────────────────────────────────────────────────────────┐   │  │ │
│  │  │  │            get_5xx_root_cause_analysis()                    │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  │  1. _extract_5xx_errors()     ──► CloudWatch Logs Insights  │   │  │ │
│  │  │  │  2. _analyze_patterns()       ──► Group by status, endpoint │   │  │ │
│  │  │  │  3. _check_infrastructure()   ──► CloudWatch Metrics        │   │  │ │
│  │  │  │  4. _determine_root_cause()   ──► Correlation analysis      │   │  │ │
│  │  │  │  5. _generate_recommendations()──► Best practices           │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  └────────────────────────────────────────────────────────────┘   │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│                    ┌─────────────────┐    ┌─────────────────┐                │
│                    │  CloudWatch     │    │   CloudWatch    │                │
│                    │     Logs        │    │    Metrics      │                │
│                    │                 │    │                 │                │
│                    │ /aws/ec2/...    │    │ CPUUtilization  │                │
│                    │ /aws/alb/...    │    │ MemoryUtil...   │                │
│                    └─────────────────┘    └─────────────────┘                │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 7. Error Code Classification

| Status Code | Ý nghĩa | Nguyên nhân phổ biến | Giải pháp |
|-------------|---------|---------------------|-----------|
| **500** | Internal Server Error | Application crash, unhandled exception | Check application logs, fix code bugs |
| **502** | Bad Gateway | Backend không phản hồi, Lambda error | Check target health, Lambda logs |
| **503** | Service Unavailable | Không có healthy target, overloaded | Scale out, check health checks |
| **504** | Gateway Timeout | Backend xử lý quá timeout | Increase timeout, optimize backend |

## 8. Data Flow Summary

```
┌─────────┐    Natural      ┌──────────┐    Tool      ┌────────┐    Logs     ┌───────────┐
│ DevOps  │───Language────►│  Claude  │───Select───►│ Lambda │───Query───►│CloudWatch │
│         │    Question     │   AI     │   API       │        │            │   Logs    │
└─────────┘                 └──────────┘             └────────┘            └───────────┘
     ▲                           │                       │                      │
     │                           │                       │                      │
     │    Vietnamese             │                       │    JSON Logs         │
     │    Analysis               │                       │◄─────────────────────┘
     │    Report                 │                       │
     │                           │                       │ Analyze + Correlate
     │                           │    Structured         │    with Metrics
     │                           │◄──Response───────────│
     │                           │                       │
     │◄──────────────────────────┘                       │
     │    Human-readable                                 │
     │    Vietnamese response                            │
     │                                                   │
```

---

**Document Version**: 1.0  
**Created**: 2025-12-25  
**Author**: AIOps System Documentation
