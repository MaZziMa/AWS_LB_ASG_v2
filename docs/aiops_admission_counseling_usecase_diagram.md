# Use Case Diagram: AI-Courses Tư Vấn Tuyển Sinh HUTECH

## 1. Tổng quan hệ thống

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                 AI-Courses Admission Counseling Architecture                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│    ┌──────────────┐       ┌──────────────┐                                       │
│    │  Học sinh    │       │  Phụ huynh   │                                       │
│    │  (Student)   │       │  (Parent)    │                                       │
│    └──────┬───────┘       └──────┬───────┘                                       │
│           │                      │                                               │
│           └──────────┬───────────┘                                               │
│                      │ "Ngành AI điều kiện thế nào?"                             │
│                      ▼                                                           │
│    ┌─────────────────────────────────────────┐                                   │
│    │           Web/Mobile App                │                                   │
│    │  ┌─────────────────────────────────┐    │                                   │
│    │  │    Chat Interface (KnowledgeBase)   │                                   │
│    │  │    - Input: Câu hỏi tiếng Việt  │    │                                   │
│    │  │    - Output: Tư vấn chi tiết    │    │                                   │
│    │  └─────────────────────────────────┘    │                                   │
│    └────────────────┬────────────────────────┘                                   │
│                     │ POST /api/customer/ask                                     │
│                     ▼                                                            │
│    ┌─────────────────────────────────────────┐                                   │
│    │         Amazon Bedrock Agent            │                                   │
│    │  ┌─────────────────────────────────┐    │                                   │
│    │  │   Claude AI (Foundation Model)  │    │                                   │
│    │  │   - Hiểu câu hỏi tiếng Việt     │    │                                   │
│    │  │   - Chọn tool phù hợp           │    │                                   │
│    │  │   - Format response 6 phần      │    │                                   │
│    │  │   - Đề xuất next action         │    │                                   │
│    │  └─────────────────────────────────┘    │                                   │
│    │         Agent ID: LJCIO6MTHB            │                                   │
│    └────────────────┬────────────────────────┘                                   │
│                     │ Invoke Action Group                                        │
│                     ▼                                                            │
│    ┌─────────────────────────────────────────┐                                   │
│    │   Lambda: hutech-admission-agent        │                                   │
│    │  ┌─────────────────────────────────┐    │                                   │
│    │  │ get_program_admission_info()    │◄─── Thông tin 1 ngành                  │
│    │  │ compare_programs()              │◄─── So sánh 2 ngành                    │
│    │  │ search_scholarship_info()       │◄─── Tìm học bổng                       │
│    │  │ get_registration_links()        │◄─── Lấy link đăng ký                   │
│    │  └─────────────────────────────────┘    │                                   │
│    └────────────────┬────────────────────────┘                                   │
│                     │                                                            │
│         ┌───────────┴───────────┐                                                │
│         ▼                       ▼                                                │
│    ┌──────────────┐       ┌──────────────┐                                       │
│    │   DynamoDB   │       │  S3 Bucket   │                                       │
│    │hutech-admissions│   │ (Knowledge   │                                       │
│    │              │       │    Base)     │                                       │
│    │ - Ngành học  │       │ - FAQ docs   │                                       │
│    │ - Học phí    │       │ - Quy chế    │                                       │
│    │ - Deadline   │       │ - Hướng dẫn  │                                       │
│    │ - Học bổng   │       │              │                                       │
│    └──────────────┘       └──────────────┘                                       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Use Case Diagram (UML)

```
                           ┌──────────────────────────────────────────────────────────┐
                           │           AI-Courses Tư Vấn Tuyển Sinh                   │
                           │                                                          │
                           │  ┌────────────────────────────────────────────────────┐  │
   ┌──────────┐            │  │    (UC1) Hỏi thông tin ngành học                   │  │
   │ Học sinh │    ask     │  │    ──────────────────────────                      │  │
   │          │───────────►│  │    Tư vấn về điều kiện tuyển sinh,                 │  │
   └──────────┘            │  │    học phí, cơ hội nghề nghiệp                     │  │
                           │  └──────────────────┬─────────────────────────────────┘  │
                           │                     │ <<include>>                         │
   ┌──────────┐            │         ┌───────────┴───────────┐                        │
   │ Phụ huynh│    ask     │         ▼                       ▼                        │
   │          │───────────►│  ┌────────────────┐    ┌────────────────┐                │
   └──────────┘            │  │(UC1.1) Query   │    │(UC1.2) Format  │                │
                           │  │DynamoDB        │    │Response 6 phần │                │
                           │  └────────────────┘    └────────────────┘                │
                           │                                                          │
                           │  ┌────────────────────────────────────────────────────┐  │
                           │  │    (UC2) So sánh ngành học                         │  │
                           │  │    ──────────────────────                          │  │
                           │  │    So sánh 2 ngành: điều kiện, học phí,            │  │
                           │  │    cơ hội việc làm, độ khó                         │  │
                           │  └────────────────────────────────────────────────────┘  │
                           │                                                          │
                           │  ┌────────────────────────────────────────────────────┐  │
                           │  │    (UC3) Tìm học bổng                              │  │
                           │  │    ────────────────                                │  │
                           │  │    - Học bổng tuyển sinh                           │  │
                           │  │    - Học bổng năng lực                             │  │
                           │  │    - Học bổng doanh nghiệp                         │  │
                           │  └────────────────────────────────────────────────────┘  │
                           │                                                          │
                           │  ┌────────────────────────────────────────────────────┐  │
                           │  │    (UC4) Lấy link đăng ký                          │  │
                           │  │    ──────────────────                              │  │
                           │  │    - Link đăng ký xét tuyển                        │  │
                           │  │    - Link đặt lịch tư vấn                          │  │
                           │  │    - Hotline, Email liên hệ                        │  │
                           │  └────────────────────────────────────────────────────┘  │
                           │                                                          │
                           │  ┌────────────────────────────────────────────────────┐  │
                           │  │    (UC5) Hỏi về FAQ/Quy trình                      │  │
                           │  │    ────────────────────────                        │  │
                           │  │    Tra cứu Knowledge Base (RAG)                    │  │
                           │  │    - Thủ tục, hồ sơ                                │  │
                           │  │    - Quy chế tuyển sinh                            │  │
                           │  └────────────────────────────────────────────────────┘  │
                           │                                                          │
                           └──────────────────────────────────────────────────────────┘
```

## 3. AI Processing Flow - Cách AI hoạt động

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    🧠 CÁCH AI XỬ LÝ CÂU HỎI CỦA SINH VIÊN                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  📝 INPUT: "Mình muốn học ngành AI ở HUTECH, điều kiện như thế nào?"            │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│  BƯỚC 1: PHÂN TÍCH Ý ĐỊNH (Intent Recognition)                                  │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Claude AI phân tích câu hỏi:                                            │   │
│  │                                                                          │   │
│  │  ┌───────────────────┐                                                   │   │
│  │  │ "Mình muốn học    │──► Trích xuất:                                    │   │
│  │  │  ngành AI ở       │    ├─ Ngành: "Trí tuệ nhân tạo" (AI)              │   │
│  │  │  HUTECH, điều     │    ├─ Trường: HUTECH                              │   │
│  │  │  kiện thế nào?"   │    ├─ Intent: Hỏi điều kiện tuyển sinh            │   │
│  │  └───────────────────┘    └─ Entities: admission_requirements            │   │
│  │                                                                          │   │
│  │  AI xác định: Cần gọi tool `get_program_admission_info`                  │   │
│  │               với parameter: program_name = "Trí tuệ nhân tạo"           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│  BƯỚC 2: GỌI TOOL PHÙ HỢP (Tool Selection & Invocation)                        │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  AI có 4 tools để chọn:                                                  │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────┐                                         │   │
│  │  │ 📋 get_program_admission_   │ ◄── ✅ CHỌN (hỏi về 1 ngành cụ thể)    │   │
│  │  │    info(program_name)       │                                         │   │
│  │  ├─────────────────────────────┤                                         │   │
│  │  │ 📊 compare_programs         │ ◄── ❌ (không so sánh 2 ngành)          │   │
│  │  │    (program1, program2)     │                                         │   │
│  │  ├─────────────────────────────┤                                         │   │
│  │  │ 💰 search_scholarship_info  │ ◄── ❌ (không hỏi riêng học bổng)       │   │
│  │  │    (scholarship_type)       │                                         │   │
│  │  ├─────────────────────────────┤                                         │   │
│  │  │ 🔗 get_registration_links   │ ◄── ❌ (không hỏi link đăng ký)         │   │
│  │  │    (program_name)           │                                         │   │
│  │  └─────────────────────────────┘                                         │   │
│  │                                                                          │   │
│  │  AI gọi Lambda với payload:                                              │   │
│  │  {                                                                       │   │
│  │    "function": "get_program_admission_info",                             │   │
│  │    "parameters": [{"name": "program_name", "value": "Trí tuệ nhân tạo"}] │   │
│  │  }                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│  BƯỚC 3: LAMBDA QUERY DATABASE                                                  │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Lambda handler nhận request và query DynamoDB:                          │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │  def get_program_admission_info(parameters):                     │    │   │
│  │  │      program_name = get_param_value(parameters, 'program_name')  │    │   │
│  │  │                                                                  │    │   │
│  │  │      # Query DynamoDB by program_name                            │    │   │
│  │  │      table = dynamodb.Table('hutech-admissions')                 │    │   │
│  │  │      response = table.scan(                                      │    │   │
│  │  │          FilterExpression=Attr('program_name').eq(program_name)  │    │   │
│  │  │      )                                                           │    │   │
│  │  │                                                                  │    │   │
│  │  │      return {                                                    │    │   │
│  │  │          'statusCode': 200,                                      │    │   │
│  │  │          'body': response['Items'][0]                            │    │   │
│  │  │      }                                                           │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  │                                                                          │   │
│  │  DynamoDB trả về:                                                        │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │  {                                                               │    │   │
│  │  │    "program_name": "Trí tuệ nhân tạo",                           │    │   │
│  │  │    "admission_methods": [                                        │    │   │
│  │  │      {"method": "Xét học bạ", "condition": "TB >= 7.0"},         │    │   │
│  │  │      {"method": "Xét điểm thi TN", "condition": "A00/A01 >= 20"} │    │   │
│  │  │    ],                                                            │    │   │
│  │  │    "scholarships": [...],                                        │    │   │
│  │  │    "deadlines": [...],                                           │    │   │
│  │  │    "tuition_fee": "35-40 triệu/năm",                             │    │   │
│  │  │    ...                                                           │    │   │
│  │  │  }                                                               │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│  BƯỚC 4: AI FORMAT RESPONSE THEO TEMPLATE 6 PHẦN                               │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Claude AI nhận dữ liệu từ Lambda và format theo instruction:            │   │
│  │                                                                          │   │
│  │  Input (Raw data từ DynamoDB):        Output (Formatted response):       │   │
│  │  ┌────────────────────────┐           ┌────────────────────────────┐    │   │
│  │  │ {                      │           │ 1) 📚 Tổng quan ngành:     │    │   │
│  │  │   "program_name":      │           │    AI - Machine Learning...│    │   │
│  │  │   "Trí tuệ nhân tạo",  │  ──────►  │                            │    │   │
│  │  │   "admission_methods": │           │ 2) 📝 Hình thức tuyển:     │    │   │
│  │  │   [...],               │           │    ├─ Xét học bạ: >= 7.0   │    │   │
│  │  │   "scholarships":      │           │    └─ Xét điểm TN: >= 20   │    │   │
│  │  │   [...],               │           │                            │    │   │
│  │  │   ...                  │           │ 3) 💰 Học bổng: ...        │    │   │
│  │  │ }                      │           │ 4) 📄 Hồ sơ: ...           │    │   │
│  │  └────────────────────────┘           │ 5) 📅 Deadline: ...        │    │   │
│  │                                       │ 6) ✅ Next step: ...       │    │   │
│  │                                       │                            │    │   │
│  │                                       │ 💡 Muốn mình: [A], [B]?    │    │   │
│  │                                       └────────────────────────────┘    │   │
│  │                                                                          │   │
│  │  AI tuân theo Instruction (agent_instruction.txt):                       │   │
│  │  - LUÔN format theo template 6 phần                                      │   │
│  │  - LUÔN dùng emoji phù hợp                                               │   │
│  │  - LUÔN kết thúc bằng gợi ý next action                                  │   │
│  │  - KHÔNG BAO GIỜ bịa đặt thông tin                                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ═══════════════════════════════════════════════════════════════════════════   │
│  BƯỚC 5: TRẢ VỀ CHO SINH VIÊN                                                  │
│  ═══════════════════════════════════════════════════════════════════════════   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  Response được gửi về Web App và hiển thị cho sinh viên:                 │   │
│  │                                                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │   │
│  │  │  🤖 Agent:                                                       │    │   │
│  │  │                                                                  │    │   │
│  │  │  1) 📚 Tổng quan ngành:                                          │    │   │
│  │  │     Trí tuệ nhân tạo (AI) — Chương trình tiên tiến về ML, DL,    │    │   │
│  │  │     Computer Vision, NLP                                         │    │   │
│  │  │                                                                  │    │   │
│  │  │  2) 📝 Hình thức tuyển:                                          │    │   │
│  │  │     ├─ Xét học bạ THPT: TB >= 7.0                                │    │   │
│  │  │     └─ Xét điểm thi TN: A00/A01 >= 20 điểm                       │    │   │
│  │  │                                                                  │    │   │
│  │  │  3) 💰 Học bổng:                                                 │    │   │
│  │  │     ├─ Học bổng tuyển sinh: 50-100%                              │    │   │
│  │  │     └─ Học bổng VinAI: 100% + laptop                             │    │   │
│  │  │                                                                  │    │   │
│  │  │  4) 📄 Hồ sơ cần chuẩn bị: ...                                   │    │   │
│  │  │  5) 📅 Deadline: ...                                             │    │   │
│  │  │  6) ✅ Next step: Đăng ký tại [link]                             │    │   │
│  │  │                                                                  │    │   │
│  │  │  💡 Muốn mình: gửi link đăng ký, hay so sánh AI với CNTT?        │    │   │
│  │  └─────────────────────────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.1 Decision Tree - AI Chọn Tool Như Thế Nào?

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    🌳 DECISION TREE: AI CHỌN TOOL                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                         ┌─────────────────────┐                                 │
│                         │  Câu hỏi của SV     │                                 │
│                         └──────────┬──────────┘                                 │
│                                    │                                            │
│                                    ▼                                            │
│                    ┌───────────────────────────────┐                            │
│                    │ Phân tích: SV hỏi về gì?      │                            │
│                    └───────────────┬───────────────┘                            │
│                                    │                                            │
│           ┌────────────────────────┼────────────────────────┐                   │
│           │                        │                        │                   │
│           ▼                        ▼                        ▼                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │ Hỏi về 1 NGÀNH  │    │ Hỏi SO SÁNH    │    │ Hỏi về HỌC     │              │
│  │ cụ thể?         │    │ 2 ngành?        │    │ BỔNG?          │              │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘              │
│           │                      │                      │                       │
│           ▼                      ▼                      ▼                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │ "Ngành AI điều  │    │ "So sánh AI    │    │ "HUTECH có học │              │
│  │  kiện thế nào?" │    │  với CNTT"      │    │  bổng gì?"      │              │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘              │
│           │                      │                      │                       │
│           ▼                      ▼                      ▼                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │ TOOL:           │    │ TOOL:           │    │ TOOL:           │              │
│  │ get_program_    │    │ compare_        │    │ search_         │              │
│  │ admission_info  │    │ programs        │    │ scholarship_    │              │
│  │ (program_name)  │    │ (p1, p2)        │    │ info            │              │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘              │
│                                                                                 │
│           │                                                                     │
│           ▼                                                                     │
│  ┌─────────────────┐                                                            │
│  │ Hỏi về LINK     │                                                            │
│  │ đăng ký?        │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                     │
│           ▼                                                                     │
│  ┌─────────────────┐                                                            │
│  │ "Cho link đăng  │                                                            │
│  │  ký ngành AI"   │                                                            │
│  └────────┬────────┘                                                            │
│           │                                                                     │
│           ▼                                                                     │
│  ┌─────────────────┐                                                            │
│  │ TOOL:           │                                                            │
│  │ get_registration│                                                            │
│  │ _links          │                                                            │
│  │ (program_name)  │                                                            │
│  └─────────────────┘                                                            │
│                                                                                 │
│  ════════════════════════════════════════════════════════════════════════════  │
│                                                                                 │
│  📌 TRƯỜNG HỢP ĐẶC BIỆT:                                                        │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Câu hỏi MƠ HỒ: "Tôi muốn học ở HUTECH"                                   │   │
│  │                                                                          │   │
│  │ → AI KHÔNG gọi tool                                                      │   │
│  │ → AI hỏi lại: "Bạn quan tâm ngành nào? HUTECH có: AI, CNTT, DS..."       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Câu hỏi FAQ/Quy trình: "Xét học bạ cần giấy tờ gì?"                      │   │
│  │                                                                          │   │
│  │ → AI tra Knowledge Base (RAG) thay vì gọi tool                           │   │
│  │ → Trả về từ tài liệu FAQ đã upload lên S3                                │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Ví dụ các loại câu hỏi và cách AI xử lý

| Câu hỏi của SV | AI phân tích | Tool được gọi | Output |
|----------------|--------------|---------------|--------|
| "Ngành AI học phí bao nhiêu?" | Intent: học phí, Ngành: AI | `get_program_admission_info("Trí tuệ nhân tạo")` | Học phí: 35-40 triệu/năm |
| "So sánh CNTT với AI" | Intent: so sánh, Ngành: 2 | `compare_programs("CNTT", "AI")` | Bảng so sánh 2 ngành |
| "Học bổng 100% có không?" | Intent: học bổng | `search_scholarship_info()` | Danh sách học bổng |
| "Cho link đăng ký AI" | Intent: link, Ngành: AI | `get_registration_links("AI")` | URL + Hotline |
| "Xét học bạ cần gì?" | Intent: FAQ | Knowledge Base (RAG) | Hướng dẫn từ FAQ |
| "Tôi muốn học HUTECH" | Intent: mơ hồ | Không gọi tool | Hỏi lại ngành cụ thể |

## 4. Sequence Diagram - Luồng tư vấn chi tiết

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌───────────┐
│Học sinh │     │ Web App  │     │Bedrock Agent │     │   Lambda    │     │ DynamoDB  │
│/Phụ huynh│     │ (React)  │     │  (Claude)    │     │hutech-      │     │hutech-    │
└────┬────┘     └────┬─────┘     └──────┬───────┘     │admission    │     │admissions │
     │               │                  │             └──────┬──────┘     └─────┬─────┘
     │               │                  │                    │                  │
     │ 1. "Mình muốn │                  │                    │                  │
     │    học AI ở   │                  │                    │                  │
     │    HUTECH"    │                  │                    │                  │
     │──────────────►│                  │                    │                  │
     │               │                  │                    │                  │
     │               │ 2. POST          │                    │                  │
     │               │ /api/customer/ask│                    │                  │
     │               │─────────────────►│                    │                  │
     │               │ {question:       │                    │                  │
     │               │  "Mình muốn..."}│                    │                  │
     │               │                  │                    │                  │
     │               │                  │ 3. Phân tích:      │                  │
     │               │                  │    - Ngành: AI     │                  │
     │               │                  │    - Intent: thông │                  │
     │               │                  │      tin tuyển sinh│                  │
     │               │                  │    - Tool: get_    │                  │
     │               │                  │      program_info  │                  │
     │               │                  │                    │                  │
     │               │                  │ 4. Invoke Lambda   │                  │
     │               │                  │───────────────────►│                  │
     │               │                  │ function:          │                  │
     │               │                  │ get_program_       │                  │
     │               │                  │ admission_info     │                  │
     │               │                  │ params: {program:  │                  │
     │               │                  │ "Trí tuệ nhân tạo"}│                  │
     │               │                  │                    │                  │
     │               │                  │                    │ 5. Query by     │
     │               │                  │                    │    program_name │
     │               │                  │                    │────────────────►│
     │               │                  │                    │                  │
     │               │                  │                    │ 6. Return Item  │
     │               │                  │                    │◄────────────────│
     │               │                  │                    │ {program_name,  │
     │               │                  │                    │  admission_     │
     │               │                  │                    │  methods,       │
     │               │                  │                    │  scholarships,  │
     │               │                  │                    │  deadlines...}  │
     │               │                  │                    │                  │
     │               │                  │ 7. Structured      │                  │
     │               │                  │    Response        │                  │
     │               │                  │◄───────────────────│                  │
     │               │                  │ {statusCode: 200,  │                  │
     │               │                  │  body: {...}}      │                  │
     │               │                  │                    │                  │
     │               │                  │ 8. Format theo     │                  │
     │               │                  │    Template 6 phần │                  │
     │               │                  │    ┌────────────┐  │                  │
     │               │                  │    │1.Tổng quan │  │                  │
     │               │                  │    │2.Hình thức │  │                  │
     │               │                  │    │3.Học bổng  │  │                  │
     │               │                  │    │4.Hồ sơ     │  │                  │
     │               │                  │    │5.Deadline  │  │                  │
     │               │                  │    │6.Next step │  │                  │
     │               │                  │    └────────────┘  │                  │
     │               │                  │                    │                  │
     │               │ 9. Return        │                    │                  │
     │               │    formatted     │                    │                  │
     │               │◄─────────────────│                    │                  │
     │               │    response      │                    │                  │
     │               │                  │                    │                  │
     │ 10. Hiển thị  │                  │                    │                  │
     │     response  │                  │                    │                  │
     │     đẹp với   │                  │                    │                  │
     │     emoji     │                  │                    │                  │
     │◄──────────────│                  │                    │                  │
     │               │                  │                    │                  │
```

## 4. Chi tiết các Use Case

### UC1: Hỏi thông tin ngành học

| Thuộc tính | Mô tả |
|------------|-------|
| **Actors** | Học sinh, Phụ huynh |
| **Mục đích** | Tra cứu thông tin tuyển sinh chi tiết của một ngành cụ thể |
| **Trigger** | User hỏi câu như: "Ngành AI điều kiện thế nào?", "Học phí CNTT bao nhiêu?" |
| **Precondition** | Thông tin ngành đã có trong DynamoDB |
| **Main Flow** | 1. User đặt câu hỏi về ngành<br>2. AI phân tích intent → chọn tool `get_program_admission_info`<br>3. Lambda query DynamoDB<br>4. AI format response theo 6 phần<br>5. Trả về cho user |
| **Postcondition** | User nhận thông tin đầy đủ về ngành |
| **Output** | Response 6 phần: Tổng quan, Hình thức tuyển, Học bổng, Hồ sơ, Deadline, Next step |

### UC2: So sánh ngành học

| Thuộc tính | Mô tả |
|------------|-------|
| **Actors** | Học sinh, Phụ huynh |
| **Mục đích** | So sánh 2 ngành để quyết định chọn ngành phù hợp |
| **Trigger** | "So sánh AI và CNTT", "Ngành nào dễ xin việc hơn?" |
| **Tool** | `compare_programs(program1, program2)` |
| **Output** | Bảng so sánh: Học phí, Điều kiện, Nghề nghiệp, Điểm giống/khác |

### UC3: Tìm học bổng

| Thuộc tính | Mô tả |
|------------|-------|
| **Actors** | Học sinh, Phụ huynh |
| **Mục đích** | Tìm học bổng phù hợp với điều kiện của mình |
| **Trigger** | "Học bổng nào dễ lấy?", "HUTECH có học bổng gì?" |
| **Tool** | `search_scholarship_info(scholarship_type)` |
| **Scholarship Types** | - Học bổng tuyển sinh (25-100%)<br>- Học bổng năng lực (100%)<br>- Học bổng doanh nghiệp (50%) |

### UC4: Lấy link đăng ký

| Thuộc tính | Mô tả |
|------------|-------|
| **Actors** | Học sinh |
| **Mục đích** | Lấy link để thực hiện đăng ký xét tuyển hoặc đặt lịch tư vấn |
| **Trigger** | "Cho link đăng ký", "Đặt lịch tư vấn" |
| **Tool** | `get_registration_links(program_name)` |
| **Output** | - URL đăng ký<br>- URL đặt lịch tư vấn (Calendly)<br>- Hotline, Email |

### UC5: Hỏi về FAQ/Quy trình

| Thuộc tính | Mô tả |
|------------|-------|
| **Actors** | Học sinh, Phụ huynh |
| **Mục đích** | Tra cứu thông tin về thủ tục, quy trình |
| **Trigger** | "Xét học bạ cần giấy tờ gì?", "Quy trình nộp hồ sơ?" |
| **Data Source** | Knowledge Base (S3 → Bedrock KB) |
| **Output** | Hướng dẫn từng bước từ tài liệu FAQ |

## 5. Template Response 6 Phần

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           TEMPLATE TRẢ LỜI 6 PHẦN                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  🤖 Agent:                                                                      │
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ 1) 📚 TỔNG QUAN NGÀNH                                                     ║  │
│  ║    Mô tả ngắn 1-2 câu về ngành học                                        ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ 2) 📝 HÌNH THỨC TUYỂN                                                     ║  │
│  ║    - Xét học bạ THPT: [điều kiện]                                         ║  │
│  ║    - Xét điểm thi tốt nghiệp: [tổ hợp, điểm]                              ║  │
│  ║    - Xét chứng chỉ quốc tế: [nếu có]                                      ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ 3) 💰 HỌC BỔNG                                                            ║  │
│  ║    - [Loại HB 1]: [mức %] — [điều kiện]                                   ║  │
│  ║    - [Loại HB 2]: [mức %] — [điều kiện]                                   ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ 4) 📄 HỒ SƠ CẦN CHUẨN BỊ                                                  ║  │
│  ║    - Bản sao công chứng học bạ THPT                                       ║  │
│  ║    - Bản sao CMND/CCCD                                                    ║  │
│  ║    - Phiếu đăng ký xét tuyển                                              ║  │
│  ║    - Ảnh 3x4 (4 ảnh)                                                      ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ 5) 📅 DEADLINE & LỊCH                                                     ║  │
│  ║    - Đợt 1: 01/04 — 30/06 (ưu tiên học bổng)                              ║  │
│  ║    - Đợt 2: 01/07 — 15/08 (chính thức)                                    ║  │
│  ║    ⚠️ Kiểm tra chính xác trên cổng tuyển sinh                             ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗  │
│  ║ 6) ✅ NEXT STEP                                                           ║  │
│  ║    - Đăng ký ngay: [link]                                                 ║  │
│  ║    - Đặt lịch tư vấn: [link]                                              ║  │
│  ║    - So sánh với ngành [X]                                                ║  │
│  ╚═══════════════════════════════════════════════════════════════════════════╝  │
│                                                                                 │
│  💡 Muốn mình: gửi link đăng ký, tạo checklist hồ sơ, hay so sánh ngành khác?  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 6. Ví dụ Conversation Flow

### 🎓 Scenario A: Học sinh hỏi về ngành AI

**Học sinh hỏi:**
```
Mình muốn học ngành AI ở HUTECH, điều kiện như thế nào?
```

**AI-Courses trả lời:**
```
🤖 Agent:

1) 📚 Tổng quan ngành: 
   Trí tuệ nhân tạo (AI) — Chương trình tiên tiến về Machine Learning, 
   Deep Learning, Computer Vision, NLP

2) 📝 Hình thức tuyển:
   ├─ Xét học bạ THPT: TB 3 học kỳ >= 7.0 (ưu tiên Toán, Lý, Anh)
   ├─ Xét điểm thi TN: Tổ hợp A00/A01 >= 20 điểm
   └─ Xét chứng chỉ: Portfolio AI project (nếu có)

3) 💰 Học bổng:
   ├─ Học bổng tuyển sinh: 50-100% — Top 5% điểm xét tuyển
   └─ Học bổng VinAI: 100% + laptop AI — Thi tuyển riêng (10 suất)

4) 📄 Hồ sơ cần chuẩn bị:
   ├─ Bản sao công chứng học bạ THPT
   ├─ Bản sao CMND/CCCD
   ├─ Phiếu đăng ký xét tuyển
   ├─ Ảnh 3x4 (4 ảnh)
   └─ Portfolio (nếu có: project AI, Kaggle ranking...)

5) 📅 Deadline & Lịch:
   ├─ Đợt chính: 01/04/2026 — 15/08/2026
   └─ ⚠️ Kiểm tra chính xác trên https://tuyensinh.hutech.edu.vn

6) ✅ Next step:
   ├─ Đăng ký ngay: https://tuyensinh.hutech.edu.vn/dang-ky?major=ai
   ├─ Đặt lịch tư vấn: https://calendly.com/hutech-ai
   └─ So sánh với ngành CNTT (nếu muốn)

💡 Muốn mình: gửi link đăng ký, tạo checklist hồ sơ, hay so sánh AI với CNTT?
```

---

### 💰 Scenario B: Phụ huynh hỏi về học bổng

**Phụ huynh hỏi:**
```
HUTECH có những loại học bổng nào cho sinh viên?
```

**AI-Courses trả lời:**
```
🤖 Agent:

💰 HỌC BỔNG HUTECH 2026

┌─────────────────────────────────────────────────────────────────┐
│ 📚 HỌC BỔNG TUYỂN SINH (25-100%)                                │
├─────────────────────────────────────────────────────────────────┤
│ ├─ Mức 100%: Top 1% điểm xét tuyển toàn quốc                    │
│ ├─ Mức 50%: Top 5% điểm xét tuyển                               │
│ ├─ Mức 25%: Top 10% điểm xét tuyển                              │
│ └─ Thời hạn: 4 năm (duy trì GPA >= 3.2)                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 🏆 HỌC BỔNG NĂNG LỰC (100%)                                     │
├─────────────────────────────────────────────────────────────────┤
│ ├─ Điều kiện: Thi vòng năng lực HUTECH                          │
│ ├─ Ngày thi: Tháng 5 hàng năm                                   │
│ └─ Giới hạn: 20 suất/ngành                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 🏢 HỌC BỔNG DOANH NGHIỆP (50%)                                  │
├─────────────────────────────────────────────────────────────────┤
│ ├─ Đối tác: FPT, Viettel, MISA, VNG                             │
│ ├─ Điều kiện: Phỏng vấn với doanh nghiệp                        │
│ └─ Cam kết: Làm việc 2 năm sau tốt nghiệp                       │
└─────────────────────────────────────────────────────────────────┘

📋 LƯU Ý:
- Học bổng không cộng dồn (chỉ nhận 1 loại cao nhất)
- Deadline đăng ký học bổng năng lực: 30/04/2026

✅ Muốn con anh/chị đăng ký học bổng nào?
- Gửi form đăng ký học bổng năng lực
- Xem điều kiện chi tiết từng loại
- Tư vấn ngành phù hợp với học bổng
```

---

### 📊 Scenario C: So sánh ngành

**Học sinh hỏi:**
```
So sánh ngành AI với CNTT, ngành nào dễ xin việc hơn?
```

**AI-Courses trả lời:**
```
🤖 Agent:

📊 SO SÁNH: TRÍ TUỆ NHÂN TẠO vs CÔNG NGHỆ THÔNG TIN

┌─────────────────────┬─────────────────────┬─────────────────────┐
│                     │   🤖 AI            │   💻 CNTT           │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Học phí/năm         │ 35-40 triệu         │ 28-32 triệu         │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Điểm xét tuyển      │ A00/A01 >= 20       │ A00/A01 >= 18       │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Độ khó              │ ⭐⭐⭐⭐⭐            │ ⭐⭐⭐⭐             │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Nhu cầu thị trường  │ 📈 Tăng mạnh        │ 📈 Ổn định cao      │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Lương khởi điểm     │ 15-25 triệu         │ 12-18 triệu         │
└─────────────────────┴─────────────────────┴─────────────────────┘

🔍 ĐIỂM GIỐNG NHAU:
├─ Cùng khoa Công nghệ thông tin
├─ Cùng học nền tảng lập trình năm 1-2
└─ Cùng cơ hội thực tập tại FPT, VNG, Viettel

🔍 ĐIỂM KHÁC BIỆT:
├─ AI: Chuyên sâu Machine Learning, Deep Learning, Math nặng
├─ CNTT: Rộng hơn (Web, Mobile, Network, Security)
└─ AI: Yêu cầu Toán cao hơn (Đại số tuyến tính, Xác suất)

💡 GỢI Ý:
- Nếu bạn GIỎI TOÁN, thích NGHIÊN CỨU → AI
- Nếu bạn thích LÀM SẢN PHẨM, muốn LINH HOẠT → CNTT
- Cả 2 đều DỄ XIN VIỆC nếu có skill tốt

✅ Muốn mình: xem chi tiết chương trình AI, xem chi tiết CNTT, hay tư vấn thêm?
```

## 7. Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                 AWS Cloud                                     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         Amazon Bedrock                                   │ │
│  │  ┌───────────────────┐    ┌──────────────────────────────────────────┐  │ │
│  │  │   Customer Agent  │    │        Action Group                       │  │ │
│  │  │  (LJCIO6MTHB)     │───►│  ┌─────────────────────────────────────┐  │  │ │
│  │  │                   │    │  │     OpenAPI Schema                   │  │  │ │
│  │  │  - Claude 3.5     │    │  │  ┌─────────────────────────────────┐ │  │  │ │
│  │  │  - Vietnamese     │    │  │  │ /get_program_admission_info    │ │  │  │ │
│  │  │  - 6-part format  │    │  │  │ /compare_programs              │ │  │  │ │
│  │  │                   │    │  │  │ /search_scholarship_info       │ │  │  │ │
│  │  │  Instruction:     │    │  │  │ /get_registration_links        │ │  │  │ │
│  │  │  agent_instruction│    │  │  └─────────────────────────────────┘ │  │  │ │
│  │  │  .txt             │    │  └─────────────────────────────────────┘  │  │ │
│  │  └───────────────────┘    └──────────────────┬───────────────────────┘  │ │
│  │                                              │                          │ │
│  │  ┌───────────────────┐                       │                          │ │
│  │  │  Knowledge Base   │ ◄── RAG cho FAQ       │                          │ │
│  │  │  (S3 Documents)   │                       │                          │ │
│  │  └───────────────────┘                       │                          │ │
│  └──────────────────────────────────────────────┼──────────────────────────┘ │
│                                                 │                            │
│                                                 ▼                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         AWS Lambda                                       │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │                  hutech-admission-agent                            │  │ │
│  │  │                                                                    │  │ │
│  │  │  ┌────────────────────────────────────────────────────────────┐   │  │ │
│  │  │  │            Functions (4 tools)                              │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  │  get_program_admission_info(program_name)                   │   │  │ │
│  │  │  │  ├─ Query DynamoDB by program_name                          │   │  │ │
│  │  │  │  └─ Return: admission_methods, scholarships, deadlines      │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  │  compare_programs(program1, program2)                       │   │  │ │
│  │  │  │  ├─ Query 2 programs from DynamoDB                          │   │  │ │
│  │  │  │  └─ Return: comparison table                                │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  │  search_scholarship_info(scholarship_type)                  │   │  │ │
│  │  │  │  ├─ Scan DynamoDB for scholarships                          │   │  │ │
│  │  │  │  └─ Return: filtered scholarship list                       │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  │  get_registration_links(program_name)                       │   │  │ │
│  │  │  │  ├─ Get registration & consultation URLs                    │   │  │ │
│  │  │  │  └─ Return: links, hotline, email                           │   │  │ │
│  │  │  │                                                             │   │  │ │
│  │  │  └────────────────────────────────────────────────────────────┘   │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│         ┌─────────────────┐    ┌─────────────────┐                           │
│         │    DynamoDB     │    │    S3 Bucket    │                           │
│         │hutech-admissions│    │  Knowledge Base │                           │
│         │                 │    │                 │                           │
│         │ PK: program_id  │    │ - FAQ.md        │                           │
│         │                 │    │ - Admissions.md │                           │
│         │ Attributes:     │    │ - Scholarships  │                           │
│         │ - program_name  │    │   .md           │                           │
│         │ - description   │    │ - Contacts.md   │                           │
│         │ - admission_    │    │                 │                           │
│         │   methods       │    │                 │                           │
│         │ - scholarships  │    │                 │                           │
│         │ - deadlines     │    │                 │                           │
│         │ - tuition_fee   │    │                 │                           │
│         │ - registration_ │    │                 │                           │
│         │   url           │    │                 │                           │
│         └─────────────────┘    └─────────────────┘                           │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 8. Data Model - DynamoDB Schema

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DynamoDB: hutech-admissions                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  Primary Key: program_id (String)                                               │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ {                                                                        │   │
│  │   "program_id": "AI001",                                                 │   │
│  │   "program_name": "Trí tuệ nhân tạo",                                    │   │
│  │   "program_code": "7480107",                                             │   │
│  │   "description": "Chương trình đào tạo kỹ sư AI...",                     │   │
│  │                                                                          │   │
│  │   "admission_methods": [                                                 │   │
│  │     {"method": "Xét học bạ", "condition": "TB >= 7.0"},                  │   │
│  │     {"method": "Xét điểm thi TN", "condition": "A00/A01 >= 20"}          │   │
│  │   ],                                                                     │   │
│  │                                                                          │   │
│  │   "scholarships": [                                                      │   │
│  │     {"name": "Học bổng tuyển sinh", "amount": "50-100%",                 │   │
│  │      "condition": "Top 5% điểm xét tuyển"},                              │   │
│  │     {"name": "Học bổng VinAI", "amount": "100%",                         │   │
│  │      "condition": "Thi tuyển riêng"}                                     │   │
│  │   ],                                                                     │   │
│  │                                                                          │   │
│  │   "documents": [                                                         │   │
│  │     "Bản sao học bạ THPT",                                               │   │
│  │     "Bản sao CMND/CCCD",                                                 │   │
│  │     "Phiếu đăng ký xét tuyển"                                            │   │
│  │   ],                                                                     │   │
│  │                                                                          │   │
│  │   "deadlines": [                                                         │   │
│  │     {"round": "Đợt 1", "start": "01/04", "end": "30/06"},                │   │
│  │     {"round": "Đợt 2", "start": "01/07", "end": "15/08"}                 │   │
│  │   ],                                                                     │   │
│  │                                                                          │   │
│  │   "tuition_fee": "35-40 triệu/năm",                                      │   │
│  │   "registration_url": "https://tuyensinh.hutech.edu.vn/dang-ky?major=ai",│   │
│  │   "consultation_url": "https://calendly.com/hutech-ai",                  │   │
│  │   "contact": {                                                           │   │
│  │     "hotline": "028 5445 5555",                                          │   │
│  │     "email": "tuyensinh@hutech.edu.vn"                                   │   │
│  │   }                                                                      │   │
│  │ }                                                                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 9. Các ngành hỗ trợ

| Mã ngành | Tên ngành | Tool path |
|----------|-----------|-----------|
| `AI001` | Trí tuệ nhân tạo | `/get_program_admission_info?program_name=Trí tuệ nhân tạo` |
| `CNTT001` | Công nghệ thông tin | `/get_program_admission_info?program_name=Công nghệ thông tin` |
| `DS001` | Khoa học dữ liệu | `/get_program_admission_info?program_name=Khoa học dữ liệu` |
| `SE001` | Kỹ thuật phần mềm | `/get_program_admission_info?program_name=Kỹ thuật phần mềm` |

## 10. Error Handling

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           ERROR HANDLING FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ CASE 1: Không tìm thấy ngành (404)                                       │    │
│  │                                                                          │    │
│  │ User: "Ngành Điện tử viễn thông điều kiện thế nào?"                      │    │
│  │                                                                          │    │
│  │ AI Response:                                                             │    │
│  │ ┌────────────────────────────────────────────────────────────────────┐  │    │
│  │ │ Mình chưa có thông tin tuyển sinh cho ngành "Điện tử viễn thông"   │  │    │
│  │ │ trong hệ thống.                                                    │  │    │
│  │ │                                                                    │  │    │
│  │ │ Để được tư vấn chính xác nhất, bạn có thể:                         │  │    │
│  │ │ - 📞 Gọi hotline: 028 5445 5555                                    │  │    │
│  │ │ - 📧 Email: tuyensinh@hutech.edu.vn                                │  │    │
│  │ │ - 📅 Đặt lịch tư vấn: https://calendly.com/hutech-admission        │  │    │
│  │ │                                                                    │  │    │
│  │ │ Hoặc bạn muốn hỏi về ngành khác? HUTECH có: CNTT, AI, Khoa học     │  │    │
│  │ │ dữ liệu, Kỹ thuật phần mềm...                                      │  │    │
│  │ └────────────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ CASE 2: Câu hỏi mơ hồ                                                    │    │
│  │                                                                          │    │
│  │ User: "Tôi muốn học ở HUTECH"                                           │    │
│  │                                                                          │    │
│  │ AI Response:                                                             │    │
│  │ ┌────────────────────────────────────────────────────────────────────┐  │    │
│  │ │ Bạn quan tâm đến ngành nào cụ thể?                                 │  │    │
│  │ │                                                                    │  │    │
│  │ │ HUTECH có các ngành HOT:                                           │  │    │
│  │ │ 🤖 Trí tuệ nhân tạo (AI)                                           │  │    │
│  │ │ 💻 Công nghệ thông tin                                             │  │    │
│  │ │ 📊 Khoa học dữ liệu                                                │  │    │
│  │ │ ⚙️ Kỹ thuật phần mềm                                               │  │    │
│  │ │                                                                    │  │    │
│  │ │ Bạn muốn tìm hiểu ngành nào?                                       │  │    │
│  │ └────────────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ CASE 3: System Error (500)                                               │    │
│  │                                                                          │    │
│  │ AI Response:                                                             │    │
│  │ ┌────────────────────────────────────────────────────────────────────┐  │    │
│  │ │ Xin lỗi, hệ thống đang gặp sự cố. Bạn có thể:                      │  │    │
│  │ │ - Thử lại sau vài phút                                             │  │    │
│  │ │ - Gọi hotline: 028 5445 5555 để được tư vấn trực tiếp              │  │    │
│  │ └────────────────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 11. Glossary (Thuật ngữ)

| Thuật ngữ | Giải thích |
|-----------|------------|
| **Bedrock Agent** | Dịch vụ AWS cho phép tạo AI chatbot có khả năng gọi tools |
| **Action Group** | Nhóm các API/tools mà Agent có thể gọi |
| **Knowledge Base** | Kho tài liệu để AI tra cứu (RAG - Retrieval Augmented Generation) |
| **Tool/Function** | Các API mà AI gọi để lấy dữ liệu từ DynamoDB |
| **Session ID** | ID để duy trì ngữ cảnh conversation |
| **Template 6 phần** | Cấu trúc trả lời chuẩn: Tổng quan, Hình thức, Học bổng, Hồ sơ, Deadline, Next step |

## 12. Liên hệ

| Kênh | Thông tin |
|------|-----------|
| 📞 Hotline | 028 5445 5555 |
| 📧 Email | tuyensinh@hutech.edu.vn |
| 🌐 Website | https://tuyensinh.hutech.edu.vn |
| 📘 Facebook | https://facebook.com/tuyensinh.hutech |
| 💬 Zalo | https://zalo.me/hutechadmission |

---

**Document Version**: 1.0  
**Created**: 2025-12-25  
**Author**: AI-Courses System Documentation
