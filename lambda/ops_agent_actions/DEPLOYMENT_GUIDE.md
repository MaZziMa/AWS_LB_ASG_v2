# 🚀 Deployment Guide - Fixed Version

## ✅ Changes Deployed

### 1. **New Tool: `get_baseline_check_all`**
- **Purpose:** Composite tool that calls 4 monitoring tools internally and aggregates results
- **Solves:** Bedrock Agent's inability to reliably call multiple tools in parallel
- **Returns:** Single JSON with infrastructure, alarms, metrics, dynamodb, overall_health, issues

### 2. **Code Fixes**
- ✅ Fixed syntax error (double comma in dict)
- ✅ Added `api_base_url` to infrastructure snapshot
- ✅ Added `cloudwatch:DescribeAlarms` IAM permission
- ✅ Updated OpenAPI schema descriptions for `check_api_health` and `check_api_pagination`

### 3. **Updated OpenAPI Schema**
- ✅ Added `/get_baseline_check_all` endpoint
- ✅ Added `/get_latest_http_5xx` endpoint (structured latest 5xx finder)
- ✅ Updated descriptions to prevent agent from passing wrong URLs

### 4. **New Tool: `get_latest_http_5xx`**
- **Purpose:** Tìm lỗi 500/5xx gần nhất trong CloudWatch Logs và trả về detail đã parse
- **Solves:** Agent trả lời cụt/loop khi phải tự parse `query_cloudwatch_logs` raw results

---

## 📋 Next Steps (Bedrock Console)

### Step 1: Upload New OpenAPI Schema
```
1. Go to: AWS Console → Bedrock → Agents → CGWF5H93V2
2. Click "Edit in Agent Builder"
3. Scroll to "Action groups" section
4. Click on your existing action group (or create new one)
5. Under "Action group schema", click "Upload" or "Edit"
6. Upload: D:\AWS_LB_ASG_v2\lambda\ops_agent_actions\openapi_schema.json
7. Click "Save"
```

### Step 2: Update Agent Instructions
```
1. Still in Agent Builder
2. Scroll to top: "Instructions for the Agent" section
3. Clear existing text
4. Copy ALL content from AGENT_INSTRUCTIONS_v2.md (between the ``` ``` blocks)
5. Paste into Instructions box
6. Click "Save"
```

### Step 3: Prepare Agent
```
1. Top right corner: Click "Prepare"
2. Wait for "Agent prepared successfully" message (~30 seconds)
```

### Step 4: Update Alias
```
1. Click "Aliases" tab (left sidebar)
2. **KHÔNG tạo alias mới mỗi lần update** (quota aliases-per-agent giới hạn 10)
3. Find alias đang dùng trong hệ thống (ví dụ: `WX8RSD82ZC` / alias test hiện tại)
4. Click "Edit"
5. Ensure it points to LATEST version
6. Click "Update alias"
```

---

## 🧪 Test Prompts

### Test 1: Baseline Check (NEW TOOL)
```
Cho tôi baseline check toàn bộ hệ thống
```

**Expected Behavior:**
- ✅ Agent calls `get_baseline_check_all(minutes=15)` - ONE tool only
- ✅ Response includes all sections: Infrastructure, Alarms, Metrics, DynamoDB
- ✅ Shows `overall_health`: "healthy" or "unhealthy"
- ✅ Lists `issues` if any
- ✅ NO MORE "đang gọi..." loops

**Sample Expected Output:**
```
**Mình sẽ…**
Kiểm tra baseline toàn bộ hệ thống qua tool tổng hợp.

**Dữ liệu vừa kiểm tra**
- Tool: get_baseline_check_all(minutes=15)

**Kết quả tổng hợp**

📊 **Infrastructure**
- ASG: 2/2 instances healthy, desired=2
- ALB: active, DNS=course-management-alb-dev-xxx.elb.amazonaws.com
- TG: 2 healthy targets

🔔 **Alarms**
- 0 alarms ALARM, 3 alarms OK

📈 **ALB Metrics (15 phút)**
- Requests: 14, 5xx: 0, Latency avg: 45ms

🗄️ **DynamoDB**
- 3 tables, không throttle

**Bất thường?**
Tất cả OK ✅

**Overall Health:** healthy
```

### Test 2: Check API Health
```
Check health các endpoint API
```

**Expected:**
- ✅ Calls `check_api_health()` WITHOUT base_url param
- ✅ Lambda uses ALB DNS from environment
- ✅ Returns response times for /health, /api/courses, etc.

### Test 3: CloudWatch Alarms
```
Có alarm nào đang ALARM không?
```

**Expected:**
- ✅ Calls `get_cloudwatch_alarms()`
- ✅ Returns alarm states with summary

### Test 4: Latest 500/5xx (NEW TOOL)
```
Có lỗi 500 nào gần đây nhất? Hiện chi tiết giúp mình.
```

**Expected:**
- ✅ Calls `get_latest_http_5xx(minutes=180, limit=20)`
- ✅ Trả về chi tiết: timestamp, method, path, status_code, latency_ms, request_id, instance_id
- ✅ Không trả lời kiểu "đang tìm..." nhiều lượt

---

## 🔍 Troubleshooting

### Issue: "đang gọi..." loop persists
**Solution:** Make sure you copied the NEW instructions that mention `get_baseline_check_all`

### Issue: API timeout errors
**Check:**
```bash
# Verify Lambda has correct ALB DNS
aws lambda get-function-configuration --function-name ops-agent-actions --query 'Environment.Variables.API_BASE_URL'

# Should return: http://course-management-alb-dev-xxx.elb.amazonaws.com
```

### Issue: Tool not found
**Check:** Agent prepared after uploading new schema? Alias updated to LATEST version?

### Issue: `ServiceQuotaExceededException ... aliases-per-agent ... maximum number of resources is 10`
**Cause:** Agent đã có 10 aliases; bạn đang cố **Create** alias thứ 11.

**Fix (recommended):** Reuse alias cũ → chỉ "Edit/Update alias", không tạo mới.

**Fix (cleanup):** Xoá bớt aliases không dùng (giữ lại alias đang dùng trong app).

AWS CLI (PowerShell) gợi ý:
```powershell
# List aliases of the agent
aws bedrock-agent list-agent-aliases --agent-id <AGENT_ID> --output table

# Delete an unused alias (CHỈ xóa alias không được dùng trong app)
aws bedrock-agent delete-agent-alias --agent-id <AGENT_ID> --agent-alias-id <ALIAS_ID>
```

**Note:** Trong dự án này, EC2/user_data đang hardcode `ops_agent_alias` và `customer_agent_alias`.
Vì vậy nếu bạn đổi alias ID, cần update lại cấu hình/AMI/ASG tương ứng.

---

## 📊 Tools Inventory (NOW 9 TOOLS)

| # | Tool | Type | Status |
|---|------|------|--------|
| 1 | `get_infrastructure_snapshot` | Monitoring | ✅ |
| 2 | `query_cloudwatch_logs` | Monitoring | ✅ |
| 3 | `get_infra_metrics` | Monitoring | ✅ (with no_data_hints) |
| 4 | `get_cloudwatch_alarms` | Monitoring | ✅ |
| 5 | **`get_latest_http_5xx`** | **Monitoring** | ✅ |
| 6 | **`get_baseline_check_all`** | **Composite** | ✅ |
| 7 | `plan_instance_refresh` | Deployment | ✅ (with validation) |
| 8 | `execute_instance_refresh` | Deployment | ✅ |
| 9 | `check_api_health` | API Testing | ✅ |

---

## 🎯 Success Criteria

- [ ] Baseline check prompt trả về 1 response duy nhất (không loop)
- [ ] Response có đủ 4 sections: Infrastructure, Alarms, Metrics, DynamoDB
- [ ] Overall health status hiển thị rõ ràng
- [ ] API health check hoạt động (không URL error)
- [ ] CloudWatch alarms tool hoạt động

---

**Ready to test! Update Bedrock Console theo steps trên rồi chạy test prompts.** 🚀
