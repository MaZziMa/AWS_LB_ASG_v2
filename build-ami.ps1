# Build Custom AMI with Packer
# This script builds an AMI with the application code pre-installed

param(
    [string]$Version = "1.0.0",
    [string]$Environment = "dev",
    [string]$Region = "us-east-1"
)

Write-Host "Building custom AMI..." -ForegroundColor Green
Write-Host "Version: $Version" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan

# Check if Packer is installed
if (-not (Get-Command packer -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Packer is not installed!" -ForegroundColor Red
    Write-Host "Install from: https://www.packer.io/downloads" -ForegroundColor Yellow
    exit 1
}

# Navigate to packer directory
$PackerDir = Join-Path $PSScriptRoot "packer"
Set-Location $PackerDir

$Template = "."

# Initialize Packer
Write-Host "`nInitializing Packer..." -ForegroundColor Yellow
packer init $Template

# Validate Packer template
Write-Host "`nValidating Packer template..." -ForegroundColor Yellow
packer validate `
    -var "environment=$Environment" `
    -var "aws_region=$Region" `
    $Template

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Packer validation failed!" -ForegroundColor Red
    exit 1
}

# Build AMI
Write-Host "`nBuilding AMI (this will take 5-10 minutes)..." -ForegroundColor Yellow
$mr = packer build -machine-readable `
    -var "environment=$Environment" `
    -var "aws_region=$Region" `
    $Template

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ AMI built successfully!" -ForegroundColor Green

    $amiId = $null
    foreach ($line in $mr) {
        if ($line -match "artifact,0,id,([^,]+)$") {
            $artifactId = $Matches[1]
            if ($artifactId -match "ami-[a-z0-9]+") {
                $amiId = $Matches[0]
                break
            }
        }
    }

    if ($amiId) {
        Write-Host "AMI ID: $amiId" -ForegroundColor Cyan
        Write-Host "Tip: update terraform/terraform.tfvars: custom_ami_id = `"$amiId`"" -ForegroundColor White
    }

    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Copy the AMI ID from output above" -ForegroundColor White
    Write-Host "2. Update terraform/terraform.tfvars with: custom_ami_id = `"ami-xxxxx`"" -ForegroundColor White
    Write-Host "3. Run: cd terraform; terraform apply" -ForegroundColor White
    Write-Host "4. Trigger instance refresh to deploy" -ForegroundColor White
} else {
    Write-Host "`nERROR: AMI build failed!" -ForegroundColor Red
    exit 1
}
