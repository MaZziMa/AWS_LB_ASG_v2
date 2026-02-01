# NỘI DUNG THUYẾT TRÌNH
## Hệ thống AIOps Assistant với AWS ALB/ASG + Bedrock Agent

---

# 01 — VẤN ĐỀ

## Thực trạng vận hành hệ thống phân tán

### Khó khăn hiện tại
| Vấn đề | Mô tả |
|--------|-------|
| **Phân mảnh dữ liệu** | Metrics/Logs/Alarms nằm rải rác trên nhiều console |
| **RCA chậm** | Xác định lỗi 5xx, latency spike mất 15-30 phút thủ công |
| **Rủi ro thao tác** | Deploy/rollback thiếu cơ chế kiểm tra + xác nhận |
| **Rào cản ngôn ngữ** | Công cụ tiếng Anh, đội vận hành cần interface tiếng Việt |

### Ví dụ thực tế
```
❌ Lỗi 500 xảy ra → Mở CloudWatch → Tìm log group 
→ Viết query → Chờ kết quả → Tìm request_id 
→ Correlate metrics → Báo cáo
⏱️ Tổng: 15-30 phút
```

**📷 Gợi ý ảnh:** Screenshot CloudWatch console với nhiều tab mở, hoặc diagram "nhiều bước thủ công"

---

# 02 — GIẢI PHÁP

## AIOps Assistant - Trợ lý vận hành thông minh

### Ý tưởng cốt lõi
> **"Hỏi 1 câu tiếng Việt → Nhận kết quả đầy đủ trong vài giây"**

### Tính năng chính

| Khả năng | Mô tả |
|----------|-------|
| 🔍 **Monitoring tức thì** | Snapshot ASG/ALB/TG, alarms, metrics trong 1 lệnh |
| 🐛 **RCA tự động** | Tìm lỗi 5xx mới nhất + parse chi tiết (path, latency, request_id, instance) |
| 🚀 **Deploy an toàn** | Plan → Xác nhận → Execute với guardrails |
| 🇻🇳 **Tiếng Việt native** | Agent hiểu và trả lời tiếng Việt tự nhiên |

### Flow xử lý mới
```
✅ User: "Có lỗi 500 nào gần đây?"
→ Agent gọi get_latest_http_5xx()
→ Trả về: timestamp, endpoint, status, latency, request_id, instance
⏱️ Tổng: 3-5 giây
```

**📷 Gợi ý ảnh:** So sánh before/after (15 phút → 5 giây)

---

# 03 — KIẾN TRÚC & CÔNG NGHỆ

## Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────────────┐
│                          INTERNET                                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Application Load Balancer (ALB)                         │
│              - Health checks, SSL termination                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Target Group                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│   EC2 (ASG)   │      │   EC2 (ASG)   │      │   EC2 (ASG)   │
│   FastAPI     │      │   FastAPI     │      │   FastAPI     │
│   min=2       │      │               │      │   max=10      │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                    ┌───────────────────┐
                    │    DynamoDB       │
                    │ courses/students/ │
                    │   enrollments     │
                    └───────────────────┘
```

## AIOps Layer (Bedrock Agent)

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (React)                           │
│                    /kb → Ask AI                               │
└──────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI Backend (/api/ops/ask)                   │
└──────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│              Amazon Bedrock Agent (Claude)                    │
│              - Vietnamese prompts                             │
│              - Tool-calling orchestration                     │
└──────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│         Lambda: ops-agent-actions (Action Group)              │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │ Snapshot        │  │ Metrics         │  │ Logs Query   │  │
│  │ ASG/ALB/TG      │  │ 5xx/latency     │  │ RCA          │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │ Alarms          │  │ Latest 5xx      │  │ Instance     │  │
│  │ CloudWatch      │  │ Structured      │  │ Refresh      │  │
│  └─────────────────┘  └─────────────────┘  └──────────────┘  │
└──────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  CloudWatch   │      │  CloudWatch   │      │  Auto Scaling │
│    Logs       │      │   Metrics     │      │     API       │
└───────────────┘      └───────────────┘      └───────────────┘
```

## Tech Stack

| Layer | Công nghệ |
|-------|-----------|
| **Frontend** | React + Vite + TailwindCSS |
| **Backend** | FastAPI (Python 3.11) |
| **AI Agent** | Amazon Bedrock + Claude 3 |
| **Compute** | EC2 Auto Scaling Group |
| **Database** | DynamoDB (on-demand) |
| **Load Balancer** | Application Load Balancer |
| **IaC** | Terraform + Packer (AMI) |
| **CI/CD** | GitHub Actions |
| **Monitoring** | CloudWatch Logs/Metrics/Alarms |

**📷 Gợi ý ảnh:** Architecture diagram (Mermaid hoặc draw.io export)

---

# 04 — DEMO | 2-3 USE CASES

## Use Case 1: Tìm lỗi 500 gần nhất

### Prompt
> "Có lỗi 500/5xx nào gần đây nhất? Chi tiết."

### Expected Output
```
📍 Thời điểm: 2025-12-24 12:27:31 UTC
📍 Endpoint: POST /api/ops/ask
📍 Status: 500
📍 Latency: 3863 ms
📍 Request ID: 54959b9e-70ca-4184-9e52-980079b8c275
📍 Instance: ip-10-0-1-242.ec2.internal
📍 Log stream: i-0a5574a7d458ccff2/app
```

**📷 Gợi ý ảnh:** Screenshot chat UI với kết quả trả về

---

## Use Case 2: Baseline Check toàn bộ hệ thống

### Prompt
> "Kiểm tra tổng quan hệ thống 15 phút gần đây"

### Expected Output
```
📊 INFRASTRUCTURE
├─ ASG: 2/2 instances healthy ✅
├─ ALB: active
└─ Target Group: 2 healthy, 0 unhealthy

🔔 ALARMS
├─ OK: 4 alarms
└─ ALARM: 0 ✅

📈 METRICS (15 phút)
├─ Requests: 156
├─ 5xx errors: 0 ✅
├─ Avg latency: 45ms
└─ Healthy hosts: 2

✅ Overall: HEALTHY
```

**📷 Gợi ý ảnh:** Dashboard hoặc chat response với format đẹp

---

## Use Case 3: Rolling Deploy an toàn

### Bước 1 - Plan (tự động)
> "Lập kế hoạch rolling update ASG"

```
📋 DEPLOYMENT PLAN
├─ Instances affected: 2
├─ Min healthy: 90% (1 instance)
├─ Strategy: Rolling (1 at a time)
├─ Estimated time: 5-10 minutes
└─ Risks: Medium (ensure health checks pass)

⚠️ Xác nhận thực hiện? Gõ "ĐỒNG Ý" để tiếp tục.
```

### Bước 2 - Execute (chỉ khi user confirm)
> "ĐỒNG Ý"

```
🚀 EXECUTING...
├─ Instance refresh started
├─ Refresh ID: abc-123
└─ Monitor: AWS Console → ASG → Instance Refresh
```

**📷 Gợi ý ảnh:** Sequence diagram Plan → Confirm → Execute

---

# 05 — SO SÁNH GIẢI PHÁP CẠNH TRANH

## So sánh các phương án hiện có

| Tiêu chí | CloudWatch Console | Runbook thủ công | ChatOps truyền thống | **AIOps Assistant** |
|----------|-------------------|------------------|---------------------|---------------------|
| **Tốc độ RCA** | 15-30 phút | 10-20 phút | 5-10 phút | **3-5 giây** ✅ |
| **Ngôn ngữ** | English | Tùy SOP | English | **Tiếng Việt** ✅ |
| **Dữ liệu real-time** | ✅ | ❌ | Partial | **✅ Tool-calling** |
| **Cấu trúc output** | Raw data | Checklist | Text | **Structured JSON** ✅ |
| **Deploy safety** | Manual | Manual | Partial | **Plan+Confirm** ✅ |
| **Learning curve** | High | Medium | Low | **Low** ✅ |

## Điểm khác biệt chính

1. **Tool-calling có cấu trúc** - Parse sẵn ở backend, trả về fields rõ ràng
2. **Guardrails cho hành động nguy hiểm** - Plan/Confirm trước khi execute
3. **Một điểm vào duy nhất** - Hỏi 1 câu, nhận đủ context
4. **Tiếng Việt native** - Phù hợp đội vận hành Việt Nam

**📷 Gợi ý ảnh:** Bảng so sánh hoặc radar chart

---

# 06 — KẾ HOẠCH PHÁT TRIỂN

## Roadmap 3 giai đoạn

### 🎯 Ngắn hạn (MVP - Đang hoàn thiện)
- [x] Core monitoring tools (snapshot, metrics, alarms)
- [x] Logs query + RCA
- [x] Latest 5xx với structured output
- [x] Instance refresh với plan/confirm
- [ ] Demo ổn định end-to-end
- [ ] Documentation hoàn chỉnh

### 🚀 Trung hạn (Q1 2026)
- [ ] **RCA Playbooks tự động** - Agent đề xuất query dựa trên triệu chứng
- [ ] **Alert integration** - Khi alarm firing → Agent tóm tắt + đề xuất xử lý
- [ ] **Caching layer** - Redis/ElastiCache giảm latency 70%
- [ ] **Streaming response** - User thấy kết quả ngay, không đợi 5-10s

### 🌟 Dài hạn (Q2-Q3 2026)
- [ ] **Multi-environment** - Dev/Staging/Prod với phân quyền
- [ ] **Audit trail** - Log mọi hành động vận hành
- [ ] **Self-healing** - Auto-remediation cho các incident phổ biến
- [ ] **Knowledge Base mở rộng** - Index thêm runbooks, postmortems

**📷 Gợi ý ảnh:** Roadmap timeline hoặc Gantt chart đơn giản

---

# 07 — KẾT LUẬN

## Giá trị mang lại

### Định lượng
| Metric | Trước | Sau | Cải thiện |
|--------|-------|-----|-----------|
| Thời gian RCA | 15-30 phút | 3-5 giây | **99%** ⬇️ |
| Số bước thao tác | 10-15 bước | 1 câu hỏi | **90%** ⬇️ |
| Rủi ro deploy | Cao (manual) | Thấp (plan+confirm) | **Giảm đáng kể** |

### Định tính
- ✅ **Chuẩn hóa** quy trình vận hành
- ✅ **Giảm phụ thuộc** vào kinh nghiệm cá nhân
- ✅ **Tăng tốc** onboarding thành viên mới
- ✅ **Audit** được mọi hành động qua chat history

## Tóm tắt 3 điểm chính
1. **Biết nhanh** - Lỗi gần nhất, metrics, alarms trong giây
2. **Baseline 1 lần** - Tổng quan toàn hệ thống bằng 1 câu
3. **Deploy an toàn** - Plan/Confirm/Execute có kiểm soát

**📷 Gợi ý ảnh:** Infographic tóm tắt 3 điểm chính

---

# 08 — CƠ HỘI THƯƠNG MẠI HÓA & ĐỀ XUẤT HỢP TÁC

## Đối tượng khách hàng

| Phân khúc | Đặc điểm | Pain point |
|-----------|----------|------------|
| **SME** | 2-10 engineers, chạy workload trên AWS | Thiếu người, cần automation |
| **Enterprise** | Đội SRE 10+, multi-account | Chuẩn hóa quy trình, compliance |
| **Startup** | Scale nhanh, lean team | Muốn move fast, không muốn hire ops |

## Mô hình kinh doanh đề xuất

### Gói dịch vụ
| Tier | Nội dung | Giá tham khảo |
|------|----------|---------------|
| **Core** | ALB/ASG blueprint + monitoring tools | $500/tháng |
| **Pro** | Core + AIOps Agent + RCA automation | $1,500/tháng |
| **Enterprise** | Pro + custom integrations + SLA | Thương lượng |

### POC Partnership
- **Thời gian:** 2-4 tuần
- **Scope:** 1 hệ thống production
- **Metrics đo lường:**
  - MTTR (Mean Time To Resolution)
  - Số incident/tháng
  - Thời gian onboarding

## Chi phí vận hành (ước tính)

| Resource | Spec | Cost/tháng |
|----------|------|------------|
| EC2 (ASG min=2) | t3.micro | ~$15-20 |
| ALB | Standard | ~$20-25 |
| DynamoDB | On-demand | ~$5-10 |
| Bedrock | Claude Sonnet | ~$20-50 |
| CloudWatch | Logs + Metrics | ~$10-15 |
| **Tổng** | | **~$70-120/tháng** |

## Call to Action

> 🤝 **Đề xuất hợp tác:**
> - POC miễn phí 2 tuần cho 1 hệ thống
> - Đo lường ROI cụ thể
> - Customize theo yêu cầu riêng

**📷 Gợi ý ảnh:** QR code liên hệ hoặc logo đối tác mục tiêu

---

# PHỤ LỤC

## A. Danh sách Tools của Agent

| Tool | Chức năng |
|------|-----------|
| `get_infrastructure_snapshot` | Snapshot ASG/ALB/TG |
| `get_cloudwatch_alarms` | Liệt kê alarms |
| `get_infra_metrics` | Metrics 5xx, latency, healthy hosts |
| `query_cloudwatch_logs` | Query Logs Insights cho RCA |
| `get_latest_http_5xx` | Tìm lỗi 5xx mới nhất (structured) |
| `get_baseline_check_all` | One-stop baseline check |
| `check_api_health` | Test HTTP endpoints |
| `plan_instance_refresh` | Dry-run deploy plan |
| `execute_instance_refresh` | Execute rolling deploy |

## B. Tech Stack chi tiết

```
Frontend:
├── React 18
├── Vite 5
├── TailwindCSS 3
└── React Router 6

Backend:
├── Python 3.11
├── FastAPI 0.104
├── boto3 (AWS SDK)
├── Pydantic v2
└── uvicorn

Infrastructure:
├── Terraform 1.6
├── Packer (AMI)
└── GitHub Actions

AWS Services:
├── EC2 + Auto Scaling
├── Application Load Balancer
├── DynamoDB
├── CloudWatch (Logs/Metrics/Alarms)
├── Bedrock (Agent + Claude)
├── Lambda
└── IAM
```

## C. Cấu trúc thư mục dự án

```
AWS_LB_ASG_v2/
├── app/                    # FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── bedrock_kb.py      # RAG integration
│   └── ops_bedrock.py     # Ops agent handler
├── frontend/              # React UI
│   └── src/components/
├── lambda/                # Bedrock Action Group
│   └── ops_agent_actions/
│       ├── handler.py     # Tool implementations
│       └── openapi_schema.json
├── terraform/             # IaC
│   ├── alb.tf
│   ├── asg.tf
│   ├── dynamodb.tf
│   └── vpc.tf
├── runbooks/              # SOPs for RAG
├── docs/                  # Documentation
└── scripts/               # Automation
```
