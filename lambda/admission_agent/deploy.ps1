param(
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }),
  [string]$FunctionName = "hutech-admission-agent",
  [string]$RoleName = "hutech-admission-agent-lambda-role",
  [string]$PolicyName = "hutech-admission-agent-ddb-read",
  [string]$AdmissionsTable = "hutech-admissions",
  [string]$Runtime = "python3.11",
  [string]$Handler = "handler.lambda_handler",
  [string]$ZipPath = "build\hutech-admission-agent.zip"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$Path) {
  if (!(Test-Path $Path)) { New-Item -ItemType Directory -Path $Path | Out-Null }
}

Write-Host "Region: $Region"

# 1) Create/ensure IAM Role
$trustPolicyPath = Join-Path $PSScriptRoot "iam\lambda-trust-policy.json"
$ddbPolicyPath = Join-Path $PSScriptRoot "iam\lambda-dynamodb-policy.json"

Write-Host "Ensuring IAM role: $RoleName"
$roleArn = $null
try {
  $roleArn = (aws iam get-role --role-name $RoleName --query Role.Arn --output text) 2>$null
} catch {}

if (!$roleArn -or $roleArn -eq "None") {
  $roleArn = aws iam create-role --role-name $RoleName --assume-role-policy-document ("file://" + (Resolve-Path $trustPolicyPath).Path) --query Role.Arn --output text
  Write-Host "Created role: $roleArn"
} else {
  Write-Host "Role exists: $roleArn"
}

if (!$roleArn -or $roleArn -eq "None") {
  throw "Failed to create or read IAM role ARN for $RoleName"
}

# 2) Attach AWS managed basic execution policy (CloudWatch Logs)
aws iam attach-role-policy --role-name $RoleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole | Out-Null

# 3) Create/update inline policy for DynamoDB read access
Write-Host "Putting inline policy: $PolicyName"
aws iam put-role-policy --role-name $RoleName --policy-name $PolicyName --policy-document ("file://" + (Resolve-Path $ddbPolicyPath).Path) | Out-Null

# IAM propagation wait (minimal)
Start-Sleep -Seconds 10

# 4) Package Lambda code (handler.py + requirements)
Write-Host "Packaging Lambda to $ZipPath"
Ensure-Dir (Split-Path $ZipPath -Parent)
$buildDir = Join-Path $PSScriptRoot "build\package"
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
Ensure-Dir $buildDir

Copy-Item (Join-Path $PSScriptRoot "handler.py") (Join-Path $buildDir "handler.py")

# Install deps into package folder (boto3 is available in Lambda runtime but safe to omit; keep requirements minimal)
# If requirements.txt exists, install them.
$reqPath = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqPath) {
  $python = "python"
  try { $python = (Get-Command python).Source } catch {}
  & $python -m pip install -r $reqPath -t $buildDir | Out-Null
}

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path (Join-Path $buildDir "*") -DestinationPath $ZipPath

# 5) Create or update Lambda function
Write-Host "Ensuring Lambda function: $FunctionName"
$fnArn = $null
try {
  $fnArn = (aws lambda get-function --function-name $FunctionName --query Configuration.FunctionArn --output text --region $Region) 2>$null
} catch {}

if (!$fnArn -or $fnArn -eq "None") {
  $fnArn = aws lambda create-function `
    --function-name $FunctionName `
    --runtime $Runtime `
    --handler $Handler `
    --role $roleArn `
    --zip-file ("fileb://" + (Resolve-Path $ZipPath).Path) `
    --timeout 30 `
    --memory-size 256 `
    --environment ("Variables={ADMISSIONS_TABLE=$AdmissionsTable}") `
    --region $Region `
    --query FunctionArn --output text
  Write-Host "Created Lambda: $fnArn"
} else {
  aws lambda update-function-code --function-name $FunctionName --zip-file ("fileb://" + (Resolve-Path $ZipPath).Path) --region $Region | Out-Null
  aws lambda update-function-configuration --function-name $FunctionName --timeout 30 --memory-size 256 --environment ("Variables={ADMISSIONS_TABLE=$AdmissionsTable}") --region $Region | Out-Null
  Write-Host "Updated Lambda: $fnArn"
}

Write-Host "Role ARN (use for --role): $roleArn"
Write-Host "Lambda name: $FunctionName"
