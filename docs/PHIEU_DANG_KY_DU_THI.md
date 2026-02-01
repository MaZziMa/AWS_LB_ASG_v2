# PHIẾU ĐĂNG KÝ DỰ THI
## HỘI THI TÌM KIẾM TÀI NĂNG CNTT NĂM 2025 – LẦN THỨ 10

---

## I. THÔNG TIN THÍ SINH

| TT | MSSV | Họ và tên | Ngày sinh | Trường, Lớp | Email | Điện thoại |
|----|------|-----------|-----------|-------------|-------|------------|
| 1  |      |           |           |             |       |            |
| 2  |      |           |           |             |       |            |
| 3  |      |           |           |             |       |            |
| 4  |      |           |           |             |       |            |

---

## II. THÔNG TIN ĐỀ TÀI DỰ THI

### 1. Bảng dự thi đăng ký

☐ Bảng A: An toàn thông tin / Information Security  
☐ Bảng B: Ứng dụng trên thiết bị thông minh / Smart Device Applications  
☐ Bảng C: Ứng dụng Website / Website Applications  
☑ **Bảng D: Trí tuệ nhân tạo & Công nghệ Chuỗi khối / AI & Blockchain**  
☐ Bảng E: Mạng máy tính / Computer Networks  
☐ Bảng F: Khoa học Dữ liệu / Data Science

---

### 2. Thông tin đề tài dự thi

#### 2.1. Tên đề tài dự thi

**Xây dựng Trợ lý AIOps cho Application Load Balancer và Auto Scaling Group sử dụng Amazon Bedrock**

---

#### 2.2. Nội dung và ý tưởng

**🎯 Vấn đề cần giải quyết:**

Các hệ thống web trên AWS ngày càng phức tạp với hàng triệu dòng log mỗi ngày. Kỹ sư DevOps đang gặp khó khăn:

- ⏱️ Mất 30-60 phút để phân tích một sự cố đơn giản
- 📊 Quá tải thông tin từ CloudWatch, ALB logs, ASG activities
- 🔄 Thiếu quy trình chuẩn hóa để xử lý sự cố
- 📚 Rào cản kiến thức cho thành viên mới

**💡 Giải pháp đề xuất:**

Xây dựng **Trợ lý vận hành ảo (AIOps Assistant)** sử dụng Generative AI có khả năng:

```
     ┌─────────────────────────────────────────────────────┐
     │                  USER QUESTION                       │
     │   "Tại sao ASG scale-out lúc 3PM hôm qua?"          │
     └─────────────────────┬───────────────────────────────┘
                           │
                           ▼
     ┌─────────────────────────────────────────────────────┐
     │              🔍 KNOWLEDGE BASE (RAG)                 │
     │   • ALB Access Logs    • ASG Activities             │
     │   • CloudWatch Alarms  • Runbooks/SOPs              │
     └─────────────────────┬───────────────────────────────┘
                           │
                           ▼
     ┌─────────────────────────────────────────────────────┐
     │              🤖 AI ANALYSIS (Claude/DeepSeek)        │
     │   • Phân tích context từ logs                       │
     │   • Tìm nguyên nhân gốc rễ                          │
     │   • Sinh câu trả lời có trích dẫn                   │
     └─────────────────────┬───────────────────────────────┘
                           │
                           ▼
     ┌─────────────────────────────────────────────────────┐
     │              📋 ACTIONABLE RESPONSE                  │
     │   "ASG scale-out do alarm high-cpu-alarm trigger    │
     │    khi CPU > 70%. Xem runbook: RUNBOOK-ALB-5XX.md"  │
     └─────────────────────────────────────────────────────┘
```

---

#### 2.3. Cơ sở lý thuyết và công nghệ sử dụng

**📚 Cơ sở lý thuyết:**

- **AIOps (AI for IT Operations):** Ứng dụng AI vào vận hành CNTT để tự động hóa giám sát, phát hiện bất thường, và phân tích nguyên nhân sự cố.

- **RAG (Retrieval-Augmented Generation):** Kỹ thuật kết hợp truy xuất thông tin từ kho tri thức với khả năng sinh văn bản của LLM, giúp AI trả lời chính xác và có trích dẫn nguồn.

- **LLM (Large Language Model):** Mô hình ngôn ngữ lớn (Claude, DeepSeek) có khả năng hiểu ngữ cảnh và sinh câu trả lời tự nhiên.

**🛠️ Công nghệ sử dụng:**

```
┌────────────────────────────────────────────────────────────────────┐
│                        TECHNOLOGY STACK                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  🧠 AI LAYER                                                       │
│  ├── Amazon Bedrock (Foundation Models)                           │
│  ├── Knowledge Base for Bedrock (RAG)                             │
│  └── Bedrock Agents (Tool Calling)                                │
│                                                                    │
│  ☁️ AWS INFRASTRUCTURE                                             │
│  ├── Application Load Balancer (ALB)                              │
│  ├── Auto Scaling Group (ASG)                                     │
│  ├── Amazon CloudWatch (Logs, Metrics, Alarms)                    │
│  ├── Amazon DynamoDB (NoSQL Database)                             │
│  └── Amazon S3 (Document Storage)                                 │
│                                                                    │
│  ⚡ SERVERLESS                                                     │
│  ├── AWS Lambda (ETL, Agent Actions)                              │
│  └── Amazon EventBridge (Scheduled Sync)                          │
│                                                                    │
│  💻 APPLICATION                                                    │
│  ├── FastAPI (Python 3.11) - Backend                              │
│  ├── React + Vite - Frontend                                      │
│  ├── Terraform - Infrastructure as Code                           │
│  └── Packer - Pre-baked AMI Builder                               │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

#### 2.4. Chức năng chính của sản phẩm

**🤖 1. Dual-Agent Architecture**

Hệ thống có 2 AI Agent chuyên biệt:

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│     👨‍🎓 CUSTOMER AGENT       │     │      🔧 OPS AGENT           │
├─────────────────────────────┤     ├─────────────────────────────┤
│ • Hỏi đáp về khóa học       │     │ • Giám sát ALB/ASG          │
│ • Thông tin đăng ký         │     │ • Phân tích sự cố           │
│ • Học phí, lịch học         │     │ • Đề xuất giải pháp         │
│ • FAQ về hệ thống           │     │ • Thực thi actions          │
├─────────────────────────────┤     ├─────────────────────────────┤
│ KB: Student Support Docs    │     │ KB: Runbooks, Logs, Metrics │
└─────────────────────────────┘     └─────────────────────────────┘
```

**📊 2. Real-time Infrastructure Monitoring**

```python
# GET /api/ops/realtime - Trả về snapshot hệ thống

{
  "timestamp": "2025-12-25T10:30:00Z",
  "asg": {
    "name": "course-management-asg-dev",
    "desired_capacity": 2,
    "instance_count": 2,
    "health_counts": {"Healthy": 2}
  },
  "target_group": {
    "target_count": 2,
    "health_counts": {"healthy": 2}
  },
  "alb": {
    "state": "active",
    "dns_name": "course-management-alb-xxx.elb.amazonaws.com"
  }
}
```

**🔍 3. Automated Root Cause Analysis**

Khi có sự cố (HTTP 5xx tăng cao, scale-out bất thường), AI tự động:

```
1️⃣  Thu thập logs từ CloudWatch Logs Insights
          ↓
2️⃣  Phân tích patterns và correlations
          ↓
3️⃣  Tìm kiếm trong[] Knowledge Base (runbooks, past incidents)
          ↓
4️⃣  Xác định nguyên nhân gốc rễ
          ↓
5️⃣  Đề xuất giải pháp + trích dẫn tài liệu
```

**⚡ 4. Actionable Insights**

Ops Agent có thể thực thi các actions sau khi được phê duyệt:

```
📋 READ-ONLY (không cần phê duyệt):
   • get_infrastructure_snapshot - Lấy trạng thái hệ thống
   • get_dynamodb_metrics - Lấy metrics DynamoDB
   • query_logs - Truy vấn CloudWatch Logs

🔐 WRITE ACTIONS (cần phê duyệt):
   • execute_asg_instance_refresh - Rolling deployment
   • execute_ddb_capacity_increase - Tăng capacity DynamoDB
```

**🔄 5. Automated Knowledge Sync**

```
CloudWatch Logs ──► EventBridge (hourly) ──► Lambda ──► S3 ──► Bedrock KB
                                                         │
                                                         ▼
                                              Auto Re-indexing
```

---

#### 2.5. Tính sáng tạo và khả năng ứng dụng, thương mại hóa

**✨ Tính sáng tạo:**

- 🔗 **Hybrid Approach:** Kết hợp giám sát truyền thống với Generative AI
- 🎯 **RAG for Ops:** Ứng dụng RAG để phân tích log real-time (cách tiếp cận mới)
- 🤖 **Dual-Agent Design:** Tách biệt domain để tối ưu độ chính xác
- 💰 **Serverless-first:** Tối ưu chi phí với pay-per-use
- 🧠 **Intent Detection:** Tự động nhận diện ý định và gọi local functions trước khi fallback về LLM

**🚀 Khả năng ứng dụng:**

```
TRƯỚC                              SAU KHI TRIỂN KHAI
─────                              ──────────────────
MTTR: 30-60 phút         ───►      MTTR: 5-10 phút
Phân tích log: 15-30'    ───►      < 1 phút (AI-assisted)
On-call escalation: 40%  ───►      15%
Knowledge transfer: 2-4w ───►      2-3 ngày
```

**💼 Thương mại hóa:**

- **SaaS Model:** AIOps-as-a-Service cho SMB/Enterprise
- **On-premise:** Triển khai private cho compliance requirements  
- **AWS Marketplace:** Add-on cho các monitoring tools
- **White-label:** Cấp phép cho MSP/Consulting firms

---

#### 2.6. Hướng phát triển trong tương lai

**📅 Ngắn hạn (3-6 tháng):**
- 🔧 Self-Healing Actions (tự động sửa lỗi với approval)
- 💬 Tích hợp Slack/Teams
- 📤 Custom Runbook Upload UI

**📅 Trung hạn (6-12 tháng):**
- ☁️ Multi-cloud Support (Azure, GCP)
- 🔍 AWS X-Ray Integration (distributed tracing)
- 💰 Cost Anomaly Detection

**📅 Dài hạn (12+ tháng):**
- 💵 FinOps Agent (tối ưu chi phí cloud)
- 🔐 Security Agent (threat detection & response)
- 📋 Compliance Agent (SOC2, HIPAA audit)

---

#### 2.7. Màn hình, hình ảnh chính của ứng dụng (Screenshots)

*(Đính kèm screenshots)*

1. **Dashboard** - Tổng quan hệ thống với số liệu Courses, Students, Enrollments

2. **Customer Chat** - Giao diện chat với Customer Agent

3. **Ops Chat** - Giao diện chat với Ops Agent

4. **Real-time Snapshot** - API response với infrastructure status

5. **Terraform State** - Infrastructure as Code management

---

Tôi xin cam đoan đề tài dự thi này do tôi (chúng tôi) tự làm và lời khai trên là đúng sự thật.

**TP. Hồ Chí Minh, ngày ...... tháng 12 năm 2025**

**Thí sinh đại diện đội**

. . . . . . . . . . . . . . . . . . . . . .
