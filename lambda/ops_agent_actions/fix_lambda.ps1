# Complete Fix for get_latest_http_5xx Tool
# Fixes Lambda environment variables and deploys updated code

$ErrorActionPreference = "Stop"

Write-Host "🔧 Complete Lambda Fix" -ForegroundColor Cyan

# Get current infrastructure info
Write-Host "`n📊 Getting infrastructure info..." -ForegroundColor Yellow

# Get ASG name
$asgName = (aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[?contains(AutoScalingGroupName, 'course-management')].AutoScalingGroupName" --output text --region us-east-1)
Write-Host "ASG: $asgName" -ForegroundColor Gray

# Get Target Group ARN
$tgArn = (aws elbv2 describe-target-groups --query "TargetGroups[?contains(TargetGroupName, 'course-management')].TargetGroupArn" --output text --region us-east-1)
Write-Host "TG: $tgArn" -ForegroundColor Gray

# Get ALB ARN
$albArn = (aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName, 'course-management')].LoadBalancerArn" --output text --region us-east-1)
Write-Host "ALB: $albArn" -ForegroundColor Gray

# Get ALB DNS
$albDns = (aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName, 'course-management')].DNSName" --output text --region us-east-1)
Write-Host "ALB DNS: $albDns" -ForegroundColor Gray

# Get Log Groups
$logGroups = (aws logs describe-log-groups --query "logGroups[?contains(logGroupName, 'course-management')].logGroupName" --output text --region us-east-1)
Write-Host "Log Groups: $logGroups" -ForegroundColor Gray

# Get DynamoDB tables
$ddbTables = (aws dynamodb list-tables --query "TableNames[?contains(@, 'course-management')]" --output text --region us-east-1)
Write-Host "DDB Tables: $ddbTables" -ForegroundColor Gray

# 1. Update Lambda environment variables
Write-Host "`n🔧 Updating Lambda environment variables..." -ForegroundColor Yellow

$envVars = @{
    AWS_REGION = "us-east-1"
    OPS_ASG_NAME = $asgName
    OPS_TARGET_GROUP_ARN = $tgArn
    OPS_ALB_ARN = $albArn
    API_BASE_URL = "http://$albDns"
    OPS_LOG_GROUPS = $logGroups -replace '\s+', ','
    OPS_DDB_TABLES = $ddbTables -replace '\s+', ','
}

$envJson = $envVars | ConvertTo-Json -Compress
Write-Host "Environment variables:" -ForegroundColor Gray
$envVars | Format-Table -AutoSize

aws lambda update-function-configuration `
    --function-name ops-agent-actions `
    --environment "Variables=$($envJson -replace '"', '\"')" `
    --region us-east-1

Write-Host "✅ Environment variables updated" -ForegroundColor Green

# 2. Wait for config update
Write-Host "`n⏳ Waiting for configuration update..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 3. Package and deploy code
Write-Host "`n📦 Creating deployment package..." -ForegroundColor Yellow
if (Test-Path "ops_agent_actions.zip") {
    Remove-Item "ops_agent_actions.zip"
}
Compress-Archive -Path "handler.py" -DestinationPath "ops_agent_actions.zip" -Force

Write-Host "`n⬆️  Updating Lambda function code..." -ForegroundColor Yellow
aws lambda update-function-code `
    --function-name ops-agent-actions `
    --zip-file fileb://ops_agent_actions.zip `
    --region us-east-1

# 4. Wait for code update
Write-Host "`n⏳ Waiting for code update..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 5. Test the function
Write-Host "`n🧪 Testing get_latest_http_5xx..." -ForegroundColor Yellow

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
$responseBody = $response.response.functionResponse.responseBody.TEXT.body | ConvertFrom-Json

Write-Host "Status: $($responseBody.timestamp)" -ForegroundColor Gray
Write-Host "Window: $($responseBody.window_minutes) minutes" -ForegroundColor Gray
Write-Host "Log Groups: $($responseBody.log_groups -join ', ')" -ForegroundColor Gray

if ($responseBody.latest) {
    Write-Host "`n✅ Found latest 5xx:" -ForegroundColor Green
    Write-Host "  Timestamp: $($responseBody.latest.timestamp)" -ForegroundColor Gray
    Write-Host "  Status: $($responseBody.latest.status_code)" -ForegroundColor Gray
    Write-Host "  Method: $($responseBody.latest.method)" -ForegroundColor Gray
    Write-Host "  Path: $($responseBody.latest.path)" -ForegroundColor Gray
    Write-Host "  Latency: $($responseBody.latest.latency_ms) ms" -ForegroundColor Gray
    Write-Host "  Instance: $($responseBody.latest.instance_id)" -ForegroundColor Gray
} else {
    Write-Host "`n✅ No 5xx errors found in the time window" -ForegroundColor Green
}

# Cleanup
Remove-Item "test_payload.json" -ErrorAction SilentlyContinue
Remove-Item "response.json" -ErrorAction SilentlyContinue

Write-Host "`n✅ Lambda fix complete!" -ForegroundColor Green
Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/CGWF5H93V2"
Write-Host "2. Click 'Prepare' button (top right)"
Write-Host "3. Wait ~30 seconds for agent to prepare"
Write-Host "4. Test with prompt: 'Tìm lỗi 500/5xx gần nhất trong CloudWatch Logs và trả về detail đã parse'"
Write-Host "`n💡 The tool should now work correctly!" -ForegroundColor Yellow
