param(
  [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } elseif ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }),
  [string]$BucketName = "hutech-student-support-kb",
  [string]$KbFolder = "kb\student_support"
)

$ErrorActionPreference = "Stop"

Write-Host "Region: $Region"
Write-Host "Bucket: $BucketName"
Write-Host "KB folder: $KbFolder"

# Ensure bucket exists
$exists = $false
try {
  aws s3api head-bucket --bucket $BucketName 2>$null | Out-Null
  $exists = $true
} catch {}

if (-not $exists) {
  Write-Host "Creating bucket..."
  if ($Region -eq "us-east-1") {
    aws s3api create-bucket --bucket $BucketName --region $Region | Out-Null
  } else {
    aws s3api create-bucket --bucket $BucketName --region $Region --create-bucket-configuration LocationConstraint=$Region | Out-Null
  }
}

# Upload KB docs
$root = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $root
$src = Join-Path $workspaceRoot $KbFolder
if (!(Test-Path $src)) {
  throw "KB folder not found: $src"
}

Write-Host "Uploading docs to s3://$BucketName/student_support/ ..."
aws s3 sync $src ("s3://" + $BucketName + "/student_support/") --region $Region | Out-Null

Write-Host "Done. Next: Create Bedrock Knowledge Base using this S3 prefix: s3://$BucketName/student_support/"
