# NỘI DUNG CHI TIẾT TỪNG SLIDE

---

# SLIDE 1: VẤN ĐỀ

## Tiêu đề
**Thực trạng vận hành hệ thống Cloud**

## Nội dung chính (bullet points)

### 😰 Dữ liệu phân mảnh
- Metrics, Logs, Alarms nằm rải rác trên nhiều console
- Mỗi lần kiểm tra phải mở 5-10 tab khác nhau
-> Khó trả lời nhanh: lỗi gần nhất là gì, ở đâu, ảnh hưởng thế nào.
### ⏱️ RCA (Root Cause Analysis) chậm
- Tìm nguyên nhân lỗi 5xx mất **15-30 phút**
- Phải viết query thủ công, correlate nhiều nguồn dữ liệu

### ⚠️ Rủi ro thao tác
- Deploy/rollback thiếu cơ chế kiểm tra
- Dễ xảy ra lỗi do thao tác vội vàng

### 🌐 Rào cản ngôn ngữ
- Công cụ AWS toàn tiếng Anh
- Đội vận hành Việt Nam cần interface thân thiện hơn

## Ví dụ minh họa (có thể làm diagram)00
```
Lỗi 500 xảy ra
    ↓
Mở CloudWatch Console
    ↓
Tìm đúng Log Group
    ↓
Viết Logs Insights query
    ↓
Chờ kết quả (~30 giây)
    ↓
Tìm request_id
    ↓
Correlate với Metrics
    ↓
Viết báo cáo

⏱️ Tổng thời gian: 15-30 phút
```

## Speaker Notes
"Đây là thực trạng mà hầu hết các đội vận hành đều gặp phải. Khi có incident, thời gian vàng để xử lý bị lãng phí vào việc tìm kiếm thông tin thay vì giải quyết vấn đề."

---

# SLIDE 2: GIẢI PHÁP

## Tiêu đề
**AIOps Assistant - Trợ lý vận hành thông minh**

## Tagline (in đậm, to)
> "Hỏi 1 câu tiếng Việt → Nhận kết quả đầy đủ trong vài giây"

## 4 Tính năng chính (icon + text)

| Icon | Tính năng | Mô tả |
|------|-----------|-------|
| 🔍 | **Monitoring tức thì** | Snapshot ASG/ALB/TG + alarms + metrics trong 1 lệnh |
| 🐛 | **RCA tự động** | Tìm lỗi 5xx mới nhất, parse chi tiết endpoint/latency/request_id |
| 🚀 | **Deploy an toàn** | Plan → Xác nhận → Execute với guardrails |
| 🇻🇳 | **Tiếng Việt native** | Hiểu và trả lời tiếng Việt tự nhiên |

## So sánh Before/After

| | Trước | Sau |
|---|-------|-----|
| **Thời gian RCA** | 15-30 phút | **3-5 giây** |
| **Số bước thao tác** | 10-15 bước | **1 câu hỏi** |
| **Yêu cầu kỹ năng** | Biết viết query | **Chỉ cần hỏi** |

## Speaker Notes
"Giải pháp của chúng tôi đơn giản hóa toàn bộ quy trình. Thay vì mở nhiều console, viết query phức tạp, người vận hành chỉ cần hỏi 1 câu bằng tiếng Việt và nhận được câu trả lời đầy đủ ngay lập tức."

---

# SLIDE 3: KIẾN TRÚC & CÔNG NGHỆ

## Tiêu đề
**Kiến trúc hệ thống**

## Phần 1: Application Layer

```
                                    ┌─────────────┐
                                    │  INTERNET   │
                                    │   (Users)   │
                                    └──────┬──────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │         ALB            │◄─── ❶ Load Balancer
                              │   (Phân phối traffic)  │     Chia đều request đến các EC2
                              └────────────┬───────────┘
                                           │
                         ┌─────────────────┼─────────────────┐
                         ▼                 ▼                 ▼
                   ┌──────────┐      ┌──────────┐      ┌──────────┐
                   │   EC2    │      │   EC2    │      │   EC2    │◄─── ❷ Auto Scaling Group
                   │ FastAPI  │      │ FastAPI  │      │ FastAPI  │     Tự động scale 2-10 instances
                   │  AZ-1a   │      │  AZ-1b   │      │  AZ-1c   │     theo CPU (>70% scale out)
                   └────┬─────┘      └────┬─────┘      └────┬─────┘
                        │                 │                 │
                        └─────────────────┼─────────────────┘
                                          │
                                          ▼
                              ┌────────────────────────┐
                              │      DynamoDB          │◄─── ❸ Database (Serverless)
                              │  courses | students    │     On-demand, tự động scale
                              │      enrollments       │
                              └────────────────────────┘
```

**Chú thích:**
| # | Component | Chức năng |
|---|-----------|-----------|
| ❶ | **ALB** | Phân phối traffic, health check, SSL termination |
| ❷ | **ASG** | Tự động tăng/giảm EC2 theo tải (min=2, max=10) |
| ❸ | **DynamoDB** | Database serverless, không cần quản lý server |

---

## Phần 2: AIOps Layer

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  👤 User: "Có lỗi 500 nào gần đây?"                                         │
│                                                                              │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │    FastAPI Backend     │◄─── ❶ API Gateway
                    │    /api/ops/ask        │     Nhận câu hỏi từ user
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │    Bedrock Agent       │◄─── ❷ AI Brain (Nova Micro)
                    │    Nova Micro          │     Hiểu ý định, quyết định
                    │    Vietnamese prompt   │     gọi tool nào
                    └────────────┬───────────┘
                                 │ Tool-calling
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Lambda: ops-agent-actions                            │◄─── ❸ Tools Hub
│                                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  Snapshot   │  │   Metrics   │  │    Logs     │  │ Latest 5xx  │        │
│   │  ASG/ALB    │  │  5xx/Latency│  │    Query    │  │             │        │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│          │                │                │                │               │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│   │   Alarms    │  │  API Health │  │  Instance   │                         │
│   │  CloudWatch │  │    Check    │  │  Refresh 🔒 │◄─── Cần confirm         │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     "ĐỒNG Ý"            │
│          │                │                │                                 │
└──────────┼────────────────┼────────────────┼─────────────────────────────────┘
           │                │                │
           ▼                ▼                ▼
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │ CloudWatch │   │ CloudWatch │   │    ASG     │◄─── ❹ AWS APIs
    │    Logs    │   │   Metrics  │   │    API     │     Dữ liệu real-time
    └────────────┘   └────────────┘   └────────────┘
```

**Chú thích:**
| # | Component | Chức năng |
|---|-----------|-----------|
| ❶ | **FastAPI** | Nhận request từ user, gọi Bedrock Agent |
| ❷ | **Bedrock Agent** | AI hiểu câu hỏi tiếng Việt, quyết định dùng tool nào |
| ❸ | **Lambda Tools** | 9 tools thực thi: snapshot, metrics, logs, deploy... |
| ❹ | **AWS APIs** | Lấy dữ liệu real-time từ CloudWatch, ASG |

---

## Phần 3: Flow tổng hợp (1 hình duy nhất)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FULL ARCHITECTURE                               │
│                                                                              │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────────┐          │
│    │  User   │ ───► │   ALB   │ ───► │   EC2   │ ───► │ DynamoDB│          │
│    │ (Admin) │      │         │      │ FastAPI │      │         │          │
│    └────┬────┘      └─────────┘      └────┬────┘      └─────────┘          │
│         │                                  │                                 │
│         │  "Có lỗi 500?"                  │                                 │
│         │                                  │                                 │
│         ▼                                  ▼                                 │
│    ┌─────────────────────────────────────────────────────────────┐          │
│    │                    AIOps Layer                              │          │
│    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │          │
│    │  │ Bedrock  │───►│  Lambda  │───►│CloudWatch│              │          │
│    │  │  Agent   │    │  Tools   │    │Logs/Metrics│            │          │
│    │  │  🤖 AI   │◄───│  🔧 9    │◄───│  📊 Data │              │          │
│    │  └──────────┘    └──────────┘    └──────────┘              │          │
│    └─────────────────────────────────────────────────────────────┘          │
│                                                                              │
│    ⏱️ Response: 3-5 giây | 📊 Data: Real-time | 🛡️ Safe: Plan+Confirm      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**3 điểm nhấn kiến trúc:**
1. **Application Layer** (trên): ALB → EC2 (ASG) → DynamoDB - xử lý business logic
2. **AIOps Layer** (dưới): Bedrock Agent → Lambda Tools → CloudWatch - giám sát & vận hành
3. **Integration**: EC2 vừa chạy app, vừa gọi Bedrock Agent qua /api/ops/ask

## Tech Stack (có thể làm logo grid)

| Layer | Công nghệ |
|-------|-----------|
| Frontend | React + Vite + TailwindCSS |
| Backend | FastAPI (Python 3.11) |
| AI | Amazon Bedrock + Claude 3 |
| Compute | EC2 Auto Scaling Group |
| Database | DynamoDB |
| IaC | Terraform + Packer |

## Speaker Notes
"Kiến trúc gồm 2 phần chính: phần Application chạy workload thật (ALB + ASG + DynamoDB), và phần AIOps là lớp AI phía trên giúp giám sát và vận hành. Điểm đặc biệt là Bedrock Agent có thể gọi các tools thông qua Lambda để lấy dữ liệu real-time."

---

# SLIDE 4: DEMO - USE CASE 1

## Tiêu đề
**Demo 1: Tìm lỗi 500 gần nhất**

## Tình huống
> Hệ thống vừa có người báo lỗi 500. Cần tìm ngay lỗi gần nhất để xử lý.

## Prompt (chat bubble style)
```
👤 User: "Có lỗi 500/5xx nào gần đây nhất? Chi tiết."
```

## Response (chat bubble style)
```
🤖 Agent:

📍 Thời điểm: 2025-12-24 12:27:31 UTC
📍 Endpoint: POST /api/ops/ask
📍 Status: 500 Internal Server Error
📍 Latency: 3,863 ms
📍 Request ID: 54959b9e-70ca-4184-9e52-980079b8c275
📍 Instance: ip-10-0-1-242.ec2.internal
📍 Log stream: i-0a5574a7d458ccff2/app

💡 Next step: Kiểm tra logs với request_id trên để xem stack trace?
```

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FLOW: TÌM LỖI 500 GẦN NHẤT                       │
└─────────────────────────────────────────────────────────────────────┘

   👤 User
    │
    │ ❶ "Có lỗi 500 gần đây?"
    │
    ▼
┌─────────────────────┐
│   FastAPI Backend   │◄─── Nhận câu hỏi tiếng Việt
│   /api/ops/ask      │
└──────────┬──────────┘
           │
           │ ❷ Gửi đến AI
           │
           ▼
┌─────────────────────┐
│   Bedrock Agent     │◄─── Hiểu ý định: "Cần tool get_latest_http_5xx"
│   🤖 AI Brain       │
└──────────┬──────────┘
           │
           │ ❸ Tool-calling
           │
           ▼
┌─────────────────────┐
│  Lambda Function    │◄─── Execute get_latest_http_5xx()
│  get_latest_http_5xx│
└──────────┬──────────┘
           │
           │ ❹ Query logs
           │
           ▼
┌─────────────────────┐
│  CloudWatch Logs    │◄─── Tìm log có status 500, sort mới nhất
│  Logs Insights      │
└──────────┬──────────┘
           │
           │ ❺ Parse kết quả
           │
           ▼
┌─────────────────────┐
│  Structured Output  │
│  ──────────────────│
│  • timestamp       │
│  • endpoint         │
│  • status: 500      │
│  • latency_ms       │
│  • request_id       │
│  • instance_id      │
└──────────┬──────────┘
           │
           │ ❻ Format tiếng Việt
           │
           ▼
   🤖 Agent Response
    │
    │ 📍 Thời điểm: 2025-12-24 12:27:31 UTC
    │ 📍 Endpoint: POST /api/ops/ask
    │ 📍 Status: 500
    │ 📍 Latency: 3,863 ms
    │ 📍 Request ID: 54959b9e...
    │
    ▼
   👤 User
      (có request_id để trace tiếp)

⏱️ Total: ~3 giây
```

**Chú thích:**
| Bước | Mô tả | Thời gian |
|------|-------|-----------|
| ❶ | User hỏi bằng tiếng Việt tự nhiên | < 1s |
| ❷-❸ | Bedrock Agent hiểu và chọn tool | < 1s |
| ❹-❺ | Query CloudWatch + parse JSON | 1-2s |
| ❻ | Format response tiếng Việt | < 1s |

## Highlight box
```
⏱️ Thời gian: 3 giây
📊 Dữ liệu: Structured, đầy đủ để trace
🔍 So với manual: 15-30 phút → 3 giây (giảm 99%)
```

## Speaker Notes
"Đây là use case phổ biến nhất. Thay vì phải viết Logs Insights query, tìm log group, đợi kết quả rồi parse thủ công, agent trả về ngay thông tin đã được cấu trúc sẵn. Request ID có thể dùng để trace tiếp nếu cần."

---

# SLIDE 5: DEMO - USE CASE 2

## Tiêu đề
**Demo 2: Baseline Check toàn bộ hệ thống**

## Tình huống
> Đầu ca trực, cần kiểm tra nhanh toàn bộ hệ thống có bình thường không.

## Prompt
```
👤 User: "Kiểm tra tổng quan hệ thống 15 phút gần đây"
```

## Response (formatted box)
```
🤖 Agent:

📊 INFRASTRUCTURE
├─ ASG: 2/2 instances healthy ✅
├─ ALB: course-management-alb-dev (active)
└─ Target Group: 2 healthy, 0 unhealthy

🔔 ALARMS
├─ OK: 4 alarms
├─ ALARM: 0 ✅
└─ INSUFFICIENT_DATA: 0

📈 METRICS (15 phút gần đây)
├─ Total Requests: 156
├─ 5xx Errors: 0 ✅
├─ Avg Latency: 45ms
├─ Healthy Hosts: 2
└─ Unhealthy Hosts: 0

🗄️ DYNAMODB
├─ Read Throttle: 0 ✅
└─ Write Throttle: 0 ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ OVERALL: HEALTHY
Không phát hiện bất thường.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Highlight
```
1 câu hỏi = 4 tools chạy song song
Kết quả tổng hợp trong 5 giây
```

## Speaker Notes
"Baseline check là việc làm đầu mỗi ca trực. Trước đây phải mở 4-5 console khác nhau, giờ chỉ cần 1 câu. Agent tự động gọi nhiều tools và tổng hợp kết quả."

---

# SLIDE 6: DEMO - USE CASE 3

## Tiêu đề
**Demo 3: Rolling Deploy an toàn**

## Tình huống
> Cần deploy version mới, muốn rolling update không downtime.

## Bước 1: Plan (hiển thị 2 chat bubbles)
```
👤 User: "Lập kế hoạch rolling update ASG"

🤖 Agent:
📋 DEPLOYMENT PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Current State
├─ ASG: course-management-asg-dev
├─ Instances: 2 running
└─ All healthy ✅

📌 Refresh Configuration  
├─ Strategy: Rolling
├─ Min Healthy: 90% (giữ ít nhất 1 instance)
├─ Instance Warmup: 120 seconds
└─ Checkpoint: Disabled

📌 Impact Analysis
├─ Instances affected: 2
├─ Estimated time: 5-10 minutes
└─ Risk Level: MEDIUM

⚠️ CONFIRMATION REQUIRED
Gõ "ĐỒNG Ý" hoặc "YES" để thực hiện.
Gõ "HỦY" để dừng lại.
```

## Bước 2: Confirm & Execute
```
👤 User: "ĐỒNG Ý"

🤖 Agent:
🚀 EXECUTING INSTANCE REFRESH...

✅ Refresh initiated successfully!
├─ Refresh ID: 7a8b9c0d-1234-5678-abcd
├─ Status: Pending
└─ Monitor: ASG Console → Instance Refresh tab

💡 Tip: Theo dõi tiến độ bằng cách hỏi
   "Tình trạng instance refresh hiện tại?"
```

## Key Point (highlight box)
```
🛡️ SAFETY GUARDRAILS
• Luôn Plan trước, không execute ngay
• Yêu cầu xác nhận rõ ràng
• Hiển thị risk assessment
```

## Speaker Notes
"Đây là tính năng quan trọng nhất về mặt an toàn. Agent KHÔNG BAO GIỜ tự động execute hành động nguy hiểm. Luôn phải plan trước, hiển thị impact, và yêu cầu user confirm rõ ràng bằng từ khóa cụ thể."

---

# SLIDE 7: SO SÁNH GIẢI PHÁP

## Tiêu đề
**So sánh với các giải pháp hiện có**

## Bảng so sánh (main content)

| Tiêu chí | CloudWatch Console | Runbook thủ công | ChatOps cũ | **AIOps Assistant** |
|----------|:------------------:|:----------------:|:----------:|:-------------------:|
| Tốc độ RCA | 15-30 phút | 10-20 phút | 5-10 phút | **3-5 giây** ✅ |
| Ngôn ngữ | English | Tùy SOP | English | **Tiếng Việt** ✅ |
| Real-time data | ✅ | ❌ | Partial | **✅ Full** |
| Output format | Raw | Checklist | Text | **Structured** ✅ |
| Deploy safety | Manual | Manual | Partial | **Plan+Confirm** ✅ |
| Learning curve | High | Medium | Low | **Low** ✅ |

## 4 Điểm khác biệt chính (icon cards)

```
┌─────────────────┐  ┌─────────────────┐
│  🔧 Tool-calling │  │  🛡️ Guardrails  │
│  với cấu trúc    │  │  cho hành động  │
│  Parse sẵn ở     │  │  nguy hiểm      │
│  backend         │  │  Plan → Confirm │
└─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│  🎯 Single       │  │  🇻🇳 Tiếng Việt  │
│  Entry Point     │  │  Native         │
│  Hỏi 1 câu,      │  │  Phù hợp đội    │
│  nhận đủ context │  │  vận hành VN    │
└─────────────────┘  └─────────────────┘
```

## Speaker Notes
"Điểm khác biệt lớn nhất so với các chatbot thông thường là tool-calling có cấu trúc - agent thực sự gọi API lấy dữ liệu real-time, không phải trả lời dựa trên training data cũ. Và có guardrails cho các hành động nguy hiểm."

---

# SLIDE 8: KẾ HOẠCH PHÁT TRIỂN

## Tiêu đề
**Roadmap phát triển**

## Timeline (3 columns hoặc horizontal timeline)

### 🎯 PHASE 1: MVP (Hiện tại)
**Hoàn thành demo ổn định**

- [x] Core monitoring tools
- [x] Logs query + RCA
- [x] Latest 5xx structured output
- [x] Instance refresh với plan/confirm
- [ ] Demo end-to-end ổn định
- [ ] Documentation hoàn chỉnh

### 🚀 PHASE 2: Enhancement (Q1 2026)
**Mở rộng tính năng**

- [ ] RCA Playbooks tự động
- [ ] Alert integration (Slack/Teams)
- [ ] Caching layer (Redis)
- [ ] Streaming response
- [ ] Multi-environment support

### 🌟 PHASE 3: Enterprise (Q2-Q3 2026)
**Production-ready**

- [ ] Role-based access control
- [ ] Audit trail đầy đủ
- [ ] Self-healing automation
- [ ] Custom runbook integration
- [ ] SLA & compliance reports

## Visual Timeline (nếu có thể vẽ)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    NOW           Q1/2026         Q2/2026         Q3/2026
     │               │               │               │
     ▼               ▼               ▼               ▼
   [MVP]  ──────►  [v1.5]  ──────►  [v2.0]  ──────►  [Enterprise]
   Demo           Enhanced        Multi-env       Production
   Ready          Features        Support         Ready
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Speaker Notes
"Roadmap chia làm 3 giai đoạn rõ ràng. Hiện tại tập trung hoàn thiện MVP để demo. Phase 2 mở rộng tính năng dựa trên feedback. Phase 3 hướng tới enterprise với compliance và audit."

---

# SLIDE 9: KẾT LUẬN

## Tiêu đề
**Kết luận & Giá trị mang lại**

## Metrics cải thiện (3 big numbers)

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│    ⏱️ 99%              📉 90%              🛡️ 100%       │
│    Giảm thời          Giảm số            Có kiểm        │
│    gian RCA           bước thao tác      soát deploy    │
│                                                          │
│    15 phút → 5 giây   10 bước → 1 câu    Plan+Confirm   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 4 Giá trị định tính (icons + text)

| | Giá trị |
|---|---------|
| ✅ | **Chuẩn hóa** quy trình vận hành - ai cũng có thể làm |
| ✅ | **Giảm phụ thuộc** vào kinh nghiệm cá nhân |
| ✅ | **Tăng tốc onboarding** - thành viên mới làm việc ngay |
| ✅ | **Audit được** mọi hành động qua chat history |

## Tóm tắt 3 điểm (visual summary)

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│     🔍       │   │     📊       │   │     🚀       │
│  BIẾT NHANH  │   │   BASELINE   │   │  DEPLOY      │
│              │   │   1 LẦN      │   │  AN TOÀN     │
│  Lỗi gần     │   │              │   │              │
│  nhất, chi   │   │  Tổng quan   │   │  Plan →      │
│  tiết ngay   │   │  hệ thống    │   │  Confirm →   │
│              │   │  bằng 1 câu  │   │  Execute     │
└──────────────┘   └──────────────┘   └──────────────┘
```

## Speaker Notes
"Tóm lại, giải pháp mang lại 3 giá trị cốt lõi: Biết nhanh - không cần chờ đợi tìm kiếm; Baseline 1 lần - tiết kiệm thời gian đầu ca; Deploy an toàn - không lo thao tác nhầm."

---

# SLIDE 10: CƠ HỘI THƯƠNG MẠI HÓA

## Tiêu đề
**Cơ hội thương mại hóa & Đề xuất hợp tác**

## Đối tượng khách hàng (3 personas)

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     🏢 SME      │  │  🏛️ Enterprise  │  │   🚀 Startup   │
│                 │  │                 │  │                 │
│  2-10 engineers │  │  10+ SRE team   │  │  Lean team      │
│  Chạy AWS       │  │  Multi-account  │  │  Scale nhanh    │
│                 │  │                 │  │                 │
│  Pain: Thiếu    │  │  Pain: Chuẩn    │  │  Pain: Muốn     │
│  người, cần     │  │  hóa quy trình, │  │  move fast,     │
│  automation     │  │  compliance     │  │  không hire ops │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Gói dịch vụ (pricing table)

| Tier | Nội dung | Giá/tháng |
|------|----------|-----------|
| **Core** | ALB/ASG blueprint + monitoring tools | $500 |
| **Pro** | Core + AIOps Agent + RCA automation | $1,500 |
| **Enterprise** | Pro + custom integrations + SLA 99.9% | Thương lượng |

## Chi phí vận hành AWS (reference)

```
┌────────────────────────────────────┐
│  💰 Chi phí AWS ước tính           │
│                                    │
│  EC2 (2x t3.micro)    $15-20      │
│  ALB                   $20-25      │
│  DynamoDB (on-demand)  $5-10      │
│  Bedrock (Claude)      $20-50      │
│  CloudWatch            $10-15      │
│  ─────────────────────────────    │
│  TỔNG                  $70-120     │
└────────────────────────────────────┘
```

## Call to Action (highlight box)

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│  🤝 ĐỀ XUẤT HỢP TÁC                                     │
│                                                          │
│  ✅ POC miễn phí 2 tuần cho 1 hệ thống                  │
│  ✅ Đo lường ROI cụ thể (MTTR, incident count)          │
│  ✅ Customize theo yêu cầu riêng                         │
│                                                          │
│  📧 Contact: [email]                                    │
│  🔗 Demo: [url]                                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Speaker Notes
"Chúng tôi đề xuất hợp tác POC 2 tuần miễn phí. Trong thời gian này sẽ tích hợp vào 1 hệ thống thật, đo lường cụ thể MTTR giảm bao nhiêu, số incident xử lý được bao nhiêu. Từ đó đánh giá ROI thực tế trước khi quyết định triển khai rộng."

---

# SLIDE BACKUP: USE CASE (BẢNG) - TƯ VẤN NGÀNH AI 2026

## Tiêu đề
**Demo: Hỏi ngành Trí tuệ nhân tạo (AI) năm 2026**

## Prompt
```
👤 User: "Trí tuệ nhân tạo (AI) năm 2026? Học phí bao nhiêu?"
```

## Flow (dạng bảng, đơn giản)

| Bước | Ai thực hiện | Làm gì | Kết quả/Output |
|------|--------------|--------|----------------|
| ❶ | User | Hỏi thông tin ngành AI 2026 | Câu hỏi tiếng Việt |
| ❷ | Bedrock Agent | Nhận diện intent: tra cứu ngành + học phí + deadline | Quyết định gọi tool |
| ❸ | Action Group `admission-tools` | Gọi `get_program_admission_info(program_name="Trí tuệ nhân tạo")` | Request tool |
| ❹ | Lambda `hutech-admission-agent` | Xử lý tool, query dữ liệu | JSON data có cấu trúc |
| ❺ | DynamoDB `hutech-admissions` | Trả record ngành (học phí, hồ sơ, deadline, link…) | Item trả về |
| ❻ | Bedrock Agent | Format câu trả lời theo 6 phần chuẩn | Output rõ ràng cho user |

## Note (1 dòng)
- Nếu Bedrock runtime timeout → user “Try again” / đổi `session-id` / tăng retry.

---

# SLIDE BACKUP: USE CASE (BẢNG) - HỖ TRỢ SINH VIÊN + TUYỂN SINH (KB)

## Tình huống
Agent hỗ trợ sinh viên/tuyển sinh: câu hỏi dạng **FAQ/quy định/thủ tục** ưu tiên tra KB; câu hỏi cần số liệu chính xác theo ngành/đợt thì gọi tool.

## Flow (dạng bảng, đơn giản)

| Loại câu hỏi | Ví dụ user hỏi | Nguồn ưu tiên | Luồng xử lý | Output |
|---|---|---|---|---|
| FAQ / thủ tục | "Xét học bạ cần giấy tờ gì?" | **Knowledge Base (RAG)** | User → Agent → Retrieve KB → Tổng hợp | Trả lời ngắn gọn + các bước |
| Chính sách / giải thích | "Học bổng thường có loại nào?" | **Knowledge Base (RAG)** | User → Agent → Retrieve KB → Tổng hợp | Danh sách + lưu ý |
| Số liệu theo ngành/đợt | "Học phí ngành AI năm 2026?" | **Tool (DynamoDB/Lambda)** | User → Agent → Call tool → JSON → Format 6 phần | Con số chính xác + link |
| Thiếu dữ liệu | "Deadline ngành X?" nhưng KB không có | Tool → nếu vẫn thiếu thì hướng dẫn liên hệ | User → Agent → (Tool/KB) → Fallback | Kênh liên hệ chính thức |

## Ghi chú
- KB đặt tại S3 (prefix) → Bedrock Knowledge Base → Agent retrieve.

---

# SLIDE BACKUP: TECH DETAILS (nếu có Q&A)

## Danh sách Tools của Agent

| Tool | Chức năng |
|------|-----------|
| `get_infrastructure_snapshot` | Snapshot ASG/ALB/TG real-time |
| `get_cloudwatch_alarms` | Liệt kê trạng thái alarms |
| `get_infra_metrics` | Metrics: 5xx, latency, healthy hosts |
| `query_cloudwatch_logs` | Query Logs Insights cho RCA |
| `get_latest_http_5xx` | Tìm lỗi 5xx mới nhất (structured) |
| `get_baseline_check_all` | One-stop baseline check |
| `check_api_health` | Test HTTP endpoints |
| `plan_instance_refresh` | Dry-run deploy plan |
| `execute_instance_refresh` | Execute rolling deploy |

## Cấu trúc dự án

```
AWS_LB_ASG_v2/
├── app/                    # FastAPI backend
│   ├── main.py            # API endpoints
│   └── ops_bedrock.py     # Bedrock integration
├── frontend/              # React UI
│   └── src/components/    # Dashboard, Ask AI
├── lambda/                # Bedrock Action Group
│   └── ops_agent_actions/ # 9 tools implementation
├── terraform/             # Infrastructure as Code
│   ├── alb.tf, asg.tf    # Compute
│   └── dynamodb.tf       # Database
├── runbooks/              # SOPs for knowledge base
└── docs/                  # Documentation
```

---

# GỢI Ý THIẾT KẾ SLIDE

## Màu sắc đề xuất
- Primary: `#FF6B35` (cam đỏ như trong ảnh)
- Secondary: `#FFE74C` (vàng highlight)
- Text: `#1A1A2E` (đen đậm)
- Background: `#FFFFFF` (trắng)

## Font
- Tiêu đề: Bold, 32-40pt
- Body: Regular, 18-24pt
- Code: Monospace (Consolas, Fira Code)

## Layout gợi ý
- Slide 1-2: 60% text, 40% visual
- Slide 3: 80% diagram
- Slide 4-6: Demo format (chat bubbles)
- Slide 7: Comparison table
- Slide 8: Timeline visual
- Slide 9-10: Summary cards

## Animations
- Slide 4-6: Appear từng chat bubble
- Slide 7: Highlight cột cuối cùng
- Slide 9: Counter animation cho metrics
