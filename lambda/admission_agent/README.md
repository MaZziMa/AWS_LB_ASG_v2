# HUTECH Admission Agent

Trợ lý tư vấn tuyển sinh thông minh sử dụng Amazon Bedrock Agent.

## Tính năng

- ✅ Tư vấn thông tin tuyển sinh (điều kiện, deadline, hồ sơ)
- ✅ Tìm kiếm học bổng
- ✅ So sánh ngành học
- ✅ Cung cấp link đăng ký & đặt lịch tư vấn
- ✅ Trả lời bằng tiếng Việt tự nhiên

> Ghi chú: Bản hiện tại ưu tiên **tools + DynamoDB** để trả về dữ liệu có cấu trúc/định danh (học phí, deadlines, hồ sơ, link) và dễ kiểm soát tính đúng/sai.

## Cấu trúc

```
admission_agent/
├── handler.py              # Lambda handler chính (4 tools)
├── openapi.json            # OpenAPI schema cho Bedrock Agent
├── agent_instruction.txt   # Agent prompt (tiếng Việt)
├── agent_instruction_minimal.txt # Prompt ngắn (khuyến nghị để tránh timeout)
├── sample_data.json        # Sample data (3 ngành: CNTT, AI, DS)
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Setup

### 1. Deploy Lambda

```powershell
# Tạo deployment package
cd lambda/admission_agent
pip install -r requirements.txt -t package/
cp handler.py package/
cd package
Compress-Archive -Path * -DestinationPath ../function.zip
cd ..

# Upload lên Lambda (hoặc dùng Terraform)
aws lambda create-function `
  --function-name hutech-admission-agent `
  --runtime python3.11 `
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role `
  --handler handler.lambda_handler `
  --zip-file fileb://function.zip `
  --timeout 30 `
  --memory-size 512
```

### 2. Tạo DynamoDB table & import data

```powershell
# Tạo table
aws dynamodb create-table `
  --table-name hutech-admissions `
  --attribute-definitions AttributeName=program_id,AttributeType=S `
  --key-schema AttributeName=program_id,KeyType=HASH `
  --billing-mode PAY_PER_REQUEST

# Import sample data
aws dynamodb batch-write-item --request-items file://sample_data_batch.json
```

*Lưu ý: Cần convert `sample_data.json` sang format batch-write hoặc dùng script Python import*

### 3. Tạo Bedrock Agent

**Via Console:**

1. Bedrock → Agents → Create Agent
2. Agent name: `hutech-admission-agent`
3. Model: `anthropic.claude-3-sonnet-20240229-v1:0`
4. Instructions: Copy từ `agent_instruction_minimal.txt` (khuyến nghị)
5. Action Group:
   - Name: `admission-tools`
   - Lambda: `hutech-admission-agent`
   - OpenAPI: Upload `openapi.json`
6. Prepare → Create Alias → Test

## Troubleshooting: Bedrock timeout (Dependency resource timeout)

Nếu bạn thấy lỗi kiểu `Dependency resource: received model timeout/error exception`, thường là do:
- Prompt quá dài/nhồi nhiều “meta-instructions” (ép `<thinking>`, `<answer>`, yêu cầu citation XML, danh sách rules quá dài).
- Model/region có spike tạm thời.

Khuyến nghị:
- Dùng prompt ngắn: `agent_instruction_minimal.txt`.
- Tránh bật prompt override phức tạp (nếu không cần).
- Giảm randomness: temperature ~0.2–0.5.
- Thử model khác (Nova Micro/Lite) cho orchestration, hoặc Claude (nếu account có access).
- Thử lại request / đổi `session-id` khi test.

## Vì sao chưa dùng Bedrock Knowledge Base (KB)?

KB (Bedrock Knowledge Bases) rất phù hợp khi bạn có **tài liệu không cấu trúc** (PDF/HTML/Markdown) và muốn agent hỏi-đáp theo nội dung tài liệu.

Trong use case tuyển sinh, nhiều phần cần **dữ liệu có cấu trúc và “authoritative”**:

- Tra cứu theo khóa định danh (`program_id`, `program_code`) và trả ra trường dữ liệu ổn định (học phí/deadline/link).
- Dễ cập nhật theo đợt (batch), dễ kiểm tra sai lệch.
- Tránh “hallucination” bằng cách tool trả JSON rõ ràng.

Vì vậy bản MVP dùng DynamoDB làm “KB có cấu trúc”, còn biến `KB_BUCKET` chỉ để mở đường cho KB ở phase sau.

Thực tế nên dùng **kết hợp**:

- DynamoDB tools: dữ liệu có cấu trúc (học phí, đợt tuyển, hồ sơ, link đăng ký, mã ngành).
- Bedrock KB: dữ liệu mô tả/giải thích dài, FAQ, quy chế, chính sách học bổng, hướng dẫn nộp hồ sơ.

## (Tuỳ chọn) Bật Bedrock Knowledge Base cho agent

### A) Chuẩn bị dữ liệu KB

- Tạo bucket S3 (ví dụ: `hutech-admission-kb`) và upload tài liệu: FAQ, chính sách học bổng, hướng dẫn đăng ký, quy chế tuyển sinh.
- Khuyến nghị: 1 file/1 chủ đề, định dạng Markdown hoặc PDF rõ heading để RAG dễ chunk.

### B) Tạo KB trong Bedrock

**Via Console (khuyến nghị):**

1. Bedrock → Knowledge Bases → Create knowledge base
2. Data source: S3 bucket ở trên
3. Chọn embedding model + vector store theo hướng dẫn console
4. Sync/ingest dữ liệu

### C) Gắn KB vào Agent

Trong agent: bật Knowledge Base (hoặc Add knowledge base) để agent dùng RAG khi cần.

### D) Quy tắc dùng KB vs Tools

- Nếu câu hỏi cần số liệu/link/deadline/hồ sơ theo ngành → gọi tool (DynamoDB).
- Nếu câu hỏi dạng “giải thích”, FAQ, quy định, chính sách → tra KB.

## Environment Variables

**Via Terraform:**

```hcl
# terraform/bedrock_admission_agent.tf
resource "aws_bedrockagent_agent" "admission" {
  agent_name              = "hutech-admission-agent"
  agent_resource_role_arn = aws_iam_role.bedrock_agent.arn
  foundation_model        = "anthropic.claude-3-sonnet-20240229-v1:0"
  instruction             = file("${path.module}/../lambda/admission_agent/agent_instruction.txt")
}

resource "aws_bedrockagent_agent_action_group" "admission_tools" {
  agent_id          = aws_bedrockagent_agent.admission.id
  action_group_name = "admission-tools"
  
  action_group_executor {
    lambda = aws_lambda_function.admission_agent.arn
  }
  
  api_schema {
    payload = file("${path.module}/../lambda/admission_agent/openapi.json")
  }
}
```

### 4. Test

**Via AWS CLI:**

```powershell
aws bedrock-agent-runtime invoke-agent `
  --agent-id AGENT_ID `
  --agent-alias-id ALIAS_ID `
  --session-id test-123 `
  --input-text "Mình muốn học ngành AI ở HUTECH, điều kiện như thế nào?"
```

**Via FastAPI (integration):**

```python
# app/admission_bedrock.py
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

def ask_admission_agent(question: str, session_id: str):
    response = bedrock_agent.invoke_agent(
        agentId='AGENT_ID',
        agentAliasId='ALIAS_ID',
        sessionId=session_id,
        inputText=question
    )
    
    # Stream response
    for event in response['completion']:
        if 'chunk' in event:
            yield event['chunk']['bytes'].decode('utf-8')
```

## Sample Queries

```
✅ "Điều kiện tuyển ngành CNTT như thế nào?"
✅ "Học bổng tuyển sinh có những loại nào?"
✅ "So sánh ngành AI và Data Science"
✅ "Deadline nộp hồ sơ đợt 1 là khi nào?"
✅ "Cho mình link đăng ký ngành CNTT"
✅ "Học phí ngành AI bao nhiêu?"
```

## Response Format

Agent luôn trả lời theo 6 phần:

1. **Tổng quan ngành** (mô tả ngắn)
2. **Hình thức tuyển** (xét học bạ, thi TN, chứng chỉ)
3. **Học bổng** (loại, mức, điều kiện)
4. **Hồ sơ cần** (documents list)
5. **Deadline** (đợt 1, 2)
6. **Next step** (link đăng ký, đặt lịch, so sánh)

## Tools

| Tool | Mô tả |
|------|-------|
| `get_program_admission_info` | Lấy thông tin tuyển sinh 1 ngành |
| `compare_programs` | So sánh 2 ngành |
| `get_registration_links` | Link đăng ký & hotline |
| `search_scholarship_info` | Tìm kiếm học bổng |

## Environment Variables

```bash
ADMISSIONS_TABLE=hutech-admissions
KB_BUCKET=hutech-admission-kb  # (optional, dùng khi bạn bật Bedrock KB/S3 docs)
```

## IAM Permissions

Lambda cần:
- `dynamodb:Scan`
- `dynamodb:GetItem`
- `dynamodb:Query` (nếu dùng GSI)

## Roadmap

- [ ] Web search fallback (khi KB thiếu)
- [ ] Admin dashboard review missing queries
- [ ] Multi-language support (English)
- [ ] Integration với CRM (Salesforce/HubSpot)
- [ ] Auto-sync data từ website HUTECH

## License

MIT
