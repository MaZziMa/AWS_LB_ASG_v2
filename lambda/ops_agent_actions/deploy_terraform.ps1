# Deploy Lambda using Terraform
# Fixes get_latest_http_5xx tool and updates environment variables

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Lambda with Terraform" -ForegroundColor Cyan

# 1. Initialize Terraform
Write-Host "`n📦 Initializing Terraform..." -ForegroundColor Yellow
terraform init

# 2. Plan
Write-Host "`n📋 Planning deployment..." -ForegroundColor Yellow
terraform plan -out=tfplan

# 3. Apply
Write-Host "`n⬆️  Applying changes..." -ForegroundColor Yellow
terraform apply tfplan

# 4. Get outputs
Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
terraform output

# 5. Test Lambda
Write-Host "`n🧪 Testing Lambda function..." -ForegroundColor Yellow

$testPayload = @{
    actionGroup = "ops_actions"
    function = "get_latest_http_5xx"
    parameters = @(
        @{ name = "minutes"; value = "180" }
        @{ name = "limit"; value = "20" }
    )
} | ConvertTo-Json -Depth 10

$testPayload | Out-File -FilePath "test_payload.json" -Encoding utf8

aws lambda invoke `
    --function-name ops-agent-actions `
    --payload file://test_payload.json `
    --region us-east-1 `
    response.json

Write-Host "`n📄 Lambda Response:" -ForegroundColor Green
$response = Get-Content response.json | ConvertFrom-Json

if ($response.response.functionResponse) {
    $body = $response.response.functionResponse.responseBody.TEXT.body | ConvertFrom-Json
    
    Write-Host "Timestamp: $($body.timestamp)" -ForegroundColor Gray
    Write-Host "Window: $($body.window_minutes) minutes" -ForegroundColor Gray
    Write-Host "Log Groups: $($body.log_groups -join ', ')" -ForegroundColor Gray
    
    if ($body.latest) {
        Write-Host "`n✅ Found latest 5xx:" -ForegroundColor Green
        Write-Host "  Status: $($body.latest.status_code)" -ForegroundColor Yellow
        Write-Host "  Method: $($body.latest.method)" -ForegroundColor Gray
        Write-Host "  Path: $($body.latest.path)" -ForegroundColor Gray
        Write-Host "  Latency: $($body.latest.latency_ms) ms" -ForegroundColor Gray
        Write-Host "  Instance: $($body.latest.instance_id)" -ForegroundColor Gray
        Write-Host "  Request ID: $($body.latest.request_id)" -ForegroundColor Gray
    } else {
        Write-Host "`n✅ No 5xx errors found (system healthy)" -ForegroundColor Green
    }
} else {
    Write-Host "Response: $($response | ConvertTo-Json -Depth 10)" -ForegroundColor Gray
}

# Cleanup
Remove-Item "test_payload.json" -ErrorAction SilentlyContinue
Remove-Item "response.json" -ErrorAction SilentlyContinue
Remove-Item "tfplan" -ErrorAction SilentlyContinue

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Go to Bedrock Console: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/CGWF5H93V2"
Write-Host "2. Click 'Prepare' (top right)"
Write-Host "3. Wait ~30 seconds"
Write-Host "4. Test with prompt: Find latest 5xx errors in CloudWatch Logs"
