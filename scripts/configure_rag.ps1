# Configures Amazon Bedrock Knowledge Base RAG for the project
# - Validates AWS CLI and credentials
# - Applies S3 bucket policy for ALB access logs and KB ingestion
# - Creates Bedrock Knowledge Base and S3 data source
# - Starts ingestion
# - Writes .env with USE_BEDROCK=true and BEDROCK_KB_ID

param(
    [string]$Region = "us-east-1",
    [string]$BucketName = "course-management-bedrock-kb-dev",
    [string]$KbName = "course-management-ops-kb",
    [string]$S3Prefix = "bedrock/"
)

$ErrorActionPreference = "Stop"

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Required command '$name' not found. Please install it."
    }
}

Write-Host "Validating prerequisites..." -ForegroundColor Cyan
Require-Command aws

# Validate AWS identity
$accountId = aws sts get-caller-identity --query Account --output text
$callerArn = aws sts get-caller-identity --query Arn --output text
if (-not $accountId) { throw "AWS credentials not configured. Run 'aws configure'." }
Write-Host "AWS Account: $accountId" -ForegroundColor Green
Write-Host "Caller ARN: $callerArn" -ForegroundColor Green

# Ensure region
$env:AWS_REGION = $Region

# S3 bucket policy allowing ALB to write access logs under bedrock/logs/alb/ and allowing KB read
Write-Host "Applying S3 bucket policy..." -ForegroundColor Cyan
$albArnPattern = "arn:aws:elasticloadbalancing:${Region}:${accountId}:loadbalancer/app/*"
$policy = @{
  Version = "2012-10-17"
  Statement = @(
    @{ # Allow ALB service to put access logs under the alb prefix
      Effect = "Allow"
      Principal = @{ Service = "elasticloadbalancing.amazonaws.com" }
      Action = @("s3:PutObject")
      Resource = "arn:aws:s3:::$BucketName/bedrock/logs/alb/*"
      Condition = @{
        StringEquals = @{ "aws:SourceAccount" = $accountId }
        ArnLike = @{ "aws:SourceArn" = $albArnPattern }
      }
    },
    @{ # Allow Bedrock KB to read bucket objects (data source)
      Sid = "AllowBedrockRead"
      Effect = "Allow"
      Principal = @{ Service = "bedrock.amazonaws.com" }
      Action = @("s3:GetObject","s3:ListBucket")
      Resource = @(
        "arn:aws:s3:::$BucketName",
        "arn:aws:s3:::$BucketName/$S3Prefix*"
      )
      Condition = @{
        StringEquals = @{ "aws:SourceAccount" = $accountId }
      }
    }
  )
} | ConvertTo-Json -Depth 6

aws s3api put-bucket-policy --bucket $BucketName --policy $policy | Out-Null
Write-Host "Bucket policy applied to $BucketName" -ForegroundColor Green

# Create an IAM role for Bedrock KB to access S3 (trust bedrock.amazonaws.com)
Write-Host "Creating/ensuring IAM role for Bedrock KB..." -ForegroundColor Cyan
$roleName = "BedrockKBAccessRole"
$assumeRole = @{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Principal = @{ Service = "bedrock.amazonaws.com" }
    Action = "sts:AssumeRole"
  })
} | ConvertTo-Json -Depth 4

# Try create role if not exists
$roleExists = aws iam get-role --role-name $roleName 2>$null
if (-not $?) {
  aws iam create-role --role-name $roleName --assume-role-policy-document $assumeRole | Out-Null
  Write-Host "Created role $roleName" -ForegroundColor Green
} else {
  Write-Host "Role $roleName exists" -ForegroundColor Yellow
}

# Attach inline policy for S3 read
$inlinePolicy = @{
  Version = "2012-10-17"
  Statement = @(@{
    Effect = "Allow"
    Action = @("s3:GetObject","s3:ListBucket")
    Resource = @(
      "arn:aws:s3:::$BucketName",
      "arn:aws:s3:::$BucketName/$S3Prefix*"
    )
  })
} | ConvertTo-Json -Depth 4

aws iam put-role-policy --role-name $roleName --policy-name "BedrockKBS3Read" --policy-document $inlinePolicy | Out-Null
Write-Host "Attached S3 read policy to role $roleName" -ForegroundColor Green

# Create Bedrock Knowledge Base
Write-Host "Creating Bedrock Knowledge Base '$KbName'..." -ForegroundColor Cyan
$retriever = @{
  type = "VECTOR"
} | ConvertTo-Json -Compress

$kbOut = aws bedrock create-knowledge-base `
  --name $KbName `
  --role-arn (aws iam get-role --role-name $roleName --query 'Role.Arn' --output text) `
  --knowledge-base-configuration @{type='VECTOR'}

if (-not $kbOut) {
  throw "Failed to create Knowledge Base"
}

$kbId = ($kbOut | ConvertFrom-Json).knowledgeBase.knowledgeBaseId
Write-Host "Knowledge Base ID: $kbId" -ForegroundColor Green

# Create S3 data source referencing the prefix (root 'bedrock/')
Write-Host "Creating S3 data source..." -ForegroundColor Cyan
$dsName = "s3-datasource"
$dsOut = aws bedrock create-data-source `
  --knowledge-base-id $kbId `
  --name $dsName `
  --data-source-configuration (@{type='S3';s3Configuration=@{bucketArn="arn:aws:s3:::$BucketName";inclusionPrefixes=@("$S3Prefix")}} | ConvertTo-Json -Compress)

$dsId = ($dsOut | ConvertFrom-Json).dataSource.dataSourceId
Write-Host "Data Source ID: $dsId" -ForegroundColor Green

# Start ingestion
Write-Host "Starting ingestion job..." -ForegroundColor Cyan
$ingestOut = aws bedrock start-ingestion-job --knowledge-base-id $kbId --data-source-id $dsId
$jobId = ($ingestOut | ConvertFrom-Json).ingestionJob.ingestionJobId
Write-Host "Ingestion Job ID: $jobId" -ForegroundColor Green

# Write .env
Write-Host "Writing .env variables..." -ForegroundColor Cyan
$envPath = Join-Path (Get-Location) ".env"
$envLines = @(
  "USE_BEDROCK=true",
  "BEDROCK_KB_ID=$kbId",
  "AWS_REGION=$Region"
)
Set-Content -Path $envPath -Value ($envLines -join [Environment]::NewLine)
Write-Host "Updated .env with Bedrock settings" -ForegroundColor Green

Write-Host "RAG configuration complete. Next steps:" -ForegroundColor Cyan
Write-Host " - Upload local data to S3 under prefix '$S3Prefix' if not already" -ForegroundColor Gray
Write-Host " - Wait for ingestion to complete, then test /ops/ask" -ForegroundColor Gray
