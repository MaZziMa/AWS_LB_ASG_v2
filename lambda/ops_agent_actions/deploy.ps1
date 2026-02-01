# Quick Deploy Script for Lambda Function
# Fixes the get_latest_http_5xx tool issue

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Lambda Function..." -ForegroundColor Cyan

# 1. Package Lambda
Write-Host "`n📦 Creating deployment package..." -ForegroundColor Yellow
if (Test-Path "ops_agent_actions.zip") {
    Remove-Item "ops_agent_actions.zip"
}
Compress-Archive -Path "handler.py" -DestinationPath "ops_agent_actions.zip" -Force

# 2. Update Lambda function
Write-Host "`n⬆️  Updating Lambda function code..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name ops-agent-actions `
    --zip-file fileb://ops_agent_actions.zip `
    --region us-east-1

# 3. Wait for update to complete
Write-Host "`n⏳ Waiting for Lambda update..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 4. Test invoke
Write-Host "`n🧪 Testing Lambda function..." -ForegroundColor Yellow
$testPayload = @{
    actionGroup = "test"
    function = "get_latest_http_5xx"
    parameters = @(
        @{ name = "minutes"; value = "60" }
        @{ name = "limit"; value = "10" }
    )
} | ConvertTo-Json -Depth 10

$testPayload | Out-File -FilePath "test_payload.json" -Encoding utf8

aws lambda invoke `
    --function-name ops-agent-actions `
    --payload file://test_payload.json `
    --region us-east-1 `
    response.json

Write-Host "`n✅ Lambda Response:" -ForegroundColor Green
Get-Content response.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Cleanup
Remove-Item "test_payload.json" -ErrorAction SilentlyContinue
Remove-Item "response.json" -ErrorAction SilentlyContinue

Write-Host "`n✅ Deployment complete!" -ForegroundColor Green
Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Go to Bedrock Console → Agents → CGWF5H93V2"
Write-Host "2. Click 'Prepare' (top right)"
Write-Host "3. Test with: 'Tìm lỗi 500/5xx gần nhất trong CloudWatch Logs'"
