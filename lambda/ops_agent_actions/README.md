# DevOps Agent Action Groups - Setup Guide

## 🎯 Overview

Thay vì dùng regex-based intent detection, ta sẽ dùng **Bedrock Agent Action Groups**.
Agent sẽ tự quyết định gọi function nào dựa trên user query và OpenAPI schema.

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Query                                   │
│                         │                                       │
│                         ▼                                       │
│              ┌──────────────────┐                              │
│              │  Bedrock Agent   │ ← Understands query          │
│              │  (LLM powered)   │                              │
│              └────────┬─────────┘                              │
│                       │                                        │
│          Agent reads OpenAPI schema                            │
│          and decides which action to call                      │
│                       │                                        │
│              ┌────────▼─────────┐                              │
│              │  Action Group    │ ← OpenAPI defines available  │
│              │  (Lambda)        │   functions and parameters   │
│              └────────┬─────────┘                              │
│                       │                                        │
│              ┌────────▼─────────┐                              │
│              │  Lambda Handler  │ ← Executes the function      │
│              │  - get_infra     │                              │
│              │  - get_ddb       │                              │
│              │  - refresh ASG   │                              │
│              │  - check API     │                              │
│              └────────┬─────────┘                              │
│                       │                                        │
│              ┌────────▼─────────┐                              │
│              │  Agent formats   │ ← Natural language response  │
│              │  response        │                              │
│              └──────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Files Created

```
lambda/ops_agent_actions/
├── handler.py           # Lambda function code
├── openapi_schema.json  # API schema for Action Group
└── README.md            # This file
```

## 🚀 Deployment Steps

### Step 1: Create Lambda Function

```bash
# Package the Lambda
cd lambda/ops_agent_actions
zip -r ops_agent_actions.zip handler.py

# Create Lambda via AWS CLI
aws lambda create-function \
  --function-name ops-agent-actions \
  --runtime python3.11 \
  --handler handler.lambda_handler \
  --role arn:aws:iam::171308902397:role/lambda-bedrock-agent-role \
  --zip-file fileb://ops_agent_actions.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{
    OPS_ASG_NAME=course-management-asg-dev,
    OPS_TARGET_GROUP_ARN=arn:aws:elasticloadbalancing:us-east-1:171308902397:targetgroup/course-management-tg-dev/xxx,
    OPS_ALB_ARN=arn:aws:elasticloadbalancing:us-east-1:171308902397:loadbalancer/app/course-management-alb-dev/xxx,
    OPS_DDB_TABLES=course-management-courses-dev,course-management-enrollments-dev,course-management-students-dev,
    API_BASE_URL=http://your-alb-dns.amazonaws.com
  }"
```

### Step 2: Create IAM Role for Lambda

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:DescribeInstanceRefreshes",
        "autoscaling:DescribeScalingActivities",
        "autoscaling:StartInstanceRefresh"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:GetMetricData"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 3: Add Resource-based Policy for Bedrock

```bash
aws lambda add-permission \
  --function-name ops-agent-actions \
  --statement-id bedrock-agent-invoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com \
  --source-arn "arn:aws:bedrock:us-east-1:171308902397:agent/CGWF5H93V2"
```

### Step 4: Create Action Group in Bedrock Console

1. Go to **Amazon Bedrock Console** → **Agents** → Select your Ops Agent (`CGWF5H93V2`)

2. Click **Edit in Agent Builder**

3. Scroll to **Action groups** → Click **Add**

4. Configure:
   - **Action group name**: `devops-operations`
   - **Description**: `Real-time DevOps operations for infrastructure monitoring and management`
   - **Action group type**: `Define with API schemas`
   - **Action group invocation**: `Select an existing Lambda function`
   - **Lambda function**: `ops-agent-actions`
   
5. **API Schema**: Upload `openapi_schema.json` or paste content

6. Click **Create**

7. **Prepare** the agent (important!)

8. Create new **Alias** or update existing one

### Step 5: Update Backend Code

After Action Groups are configured, update `bedrock_kb.py` to simply call the agent:

```python
def invoke_ops_agent(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Invoke ops agent - agent handles all routing via Action Groups."""
    return invoke_agent(OPS_AGENT_ID, query, session_id)
```

Remove all the regex-based intent detection code!

## 🧪 Testing

After setup, test with prompts:

```
# Agent will call get_infrastructure_snapshot
"Kiểm tra infra hiện tại"

# Agent will call get_dynamodb_metrics  
"DynamoDB metrics có bị throttle không?"

# Agent will call check_api_pagination
"API courses có hỗ trợ pagination không?"

# Agent will call plan_instance_refresh
"Lên kế hoạch instance refresh"

# Agent will call execute_instance_refresh (only if user confirms)
"Thực thi instance refresh ngay bây giờ"
```

## 🚨 Use case: Hệ thống vừa có người báo lỗi 500 → tìm lỗi gần nhất

Mục tiêu: khi nhận thông tin hệ thống vừa gặp HTTP 500, ops hỏi agent để lấy **lỗi 5xx gần nhất** (ưu tiên bản ghi có `request_id` để truy vết log liên quan).

### Use case diagram (Customer-friendly)

Mô tả ngắn: sơ đồ này trình bày luồng nghiệp vụ cho người không chuyên — ai báo lỗi, hệ thống phản hồi gì, và Ops làm gì tiếp theo. Không đề cập hàm hay chi tiết code.

```mermaid
flowchart LR
  A[Monitoring System\n(e.g., ALB/CW/Sentry) / User báo lỗi]:::actor
  B[Ops Engineer / On-call]:::actor

  subgraph SYSTEM[Bedrock Ops Assistant]
    direction TB
    U1([Nhận alert: HTTP 5xx])
    U2([Xác định lỗi gần nhất])
    U3([Cung cấp kết quả + bằng chứng])
    U4([Đề xuất bước tiếp theo])
  end

  A --> U1
  U1 --> U2
  U2 --> U3
  U3 --> U4
  U4 --> B

  B -->|Yêu cầu điều tra| U3
  B -->|Thực thi/Phê duyệt| U4

  classDef actor fill:#f0f8ff,stroke:#2b6cb0,stroke-width:1px;
  classDef default fill:#ffffff,stroke:#666666,stroke-width:1px;
```

### Code flowchart (theo kiến trúc dự án)

```mermaid
flowchart LR
  Reporter((Người dùng/Monitoring)):::actor -->|báo: HTTP 500| Ops((Ops Engineer)):::actor

  Ops -->|hỏi: "Tìm lỗi 500 gần nhất"| Api[FastAPI\nPOST /api/ops/ask]:::api
  Api -->|invoke| Agent[Bedrock Ops Agent\ninvoke_agent()]:::agent
  Agent -->|Action Group\n(OpenAPI operationId)| Lambda[Lambda: ops-agent-actions\nlambda_handler()]:::lambda

  subgraph UC[Use case: Tìm lỗi 500 gần nhất] 
    direction LR
    Lambda --> Action[get_latest_http_5xx(minutes, limit)]:::action
    Action --> Logs[(CloudWatch Logs Insights)]:::aws
    Logs --> Parse[Parse candidates\nchọn bản ghi mới nhất\nưu tiên có request_id]:::step
    Parse -->|có request_id| Correlate[Query correlate theo request_id\n(filter @message like /<rid>/)]:::step
    Correlate --> Result[(Kết quả)\nlatest + related.logs]:::data
    Parse -->|không có request_id| Result
  end

  Result --> Lambda
  Lambda --> Agent
  Agent --> Api
  Api --> Ops
  Ops -->|xử lý| Mitigate[Điều tra & khắc phục\n(hotfix/rollback/RCA)]:::step

  classDef actor fill:#E3F2FD,stroke:#1E88E5,stroke-width:1px;
  classDef api fill:#F3E5F5,stroke:#8E24AA,stroke-width:1px;
  classDef agent fill:#E8F5E9,stroke:#43A047,stroke-width:1px;
  classDef lambda fill:#FFF8E1,stroke:#FB8C00,stroke-width:1px;
  classDef aws fill:#E0F7FA,stroke:#00838F,stroke-width:1px;
  classDef action fill:#FFF3E0,stroke:#FB8C00,stroke-width:1px;
  classDef step fill:#F5F5F5,stroke:#616161,stroke-width:1px;
  classDef data fill:#FCE4EC,stroke:#C2185B,stroke-width:1px;
```

### Output dữ liệu (tối thiểu)

- `latest`: `{ timestamp, status_code, method, path, latency_ms, request_id, instance_id, log_stream, message }`
- `related.logs`: (tuỳ chọn) log chứa `request_id` để hỗ trợ RCA nhanh

## ✅ Benefits

| Before (Regex) | After (Action Groups) |
|----------------|----------------------|
| Must define patterns for each query | Agent understands natural language |
| Pattern order matters | Agent chooses best match |
| Hard to add new features | Just add new function + schema |
| Can't handle variations | Handles any phrasing |
| Requires code changes | No code changes for new queries |

## 🔐 Security Notes

- `execute_instance_refresh` is marked as POST and has warning in description
- Agent should ask for confirmation before executing destructive actions
- Consider adding guardrails in Bedrock for additional safety

## 📚 References

- [Bedrock Agent Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-create.html)
- [OpenAPI Schema for Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-api-schema.html)
- [Lambda Handler Format](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html)
