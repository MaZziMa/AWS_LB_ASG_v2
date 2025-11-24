# Monitor ASG Instance Refresh Progress
param(
    [string]$AsgName = "course-management-asg-dev",
    [string]$Region = "us-east-1",
    [int]$IntervalSeconds = 30
)

Write-Host "Monitoring instance refresh for ASG: $AsgName" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring`n" -ForegroundColor Yellow

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    $refresh = aws autoscaling describe-instance-refreshes `
        --auto-scaling-group-name $AsgName `
        --region $Region `
        --query 'InstanceRefreshes[0]' `
        --output json | ConvertFrom-Json
    
    $status = $refresh.Status
    $percentage = $refresh.PercentageComplete
    $reason = $refresh.StatusReason
    
    Write-Host "[$timestamp] Status: " -NoNewline
    
    switch ($status) {
        "Pending" { Write-Host $status -ForegroundColor Yellow -NoNewline }
        "InProgress" { Write-Host $status -ForegroundColor Cyan -NoNewline }
        "Successful" { Write-Host $status -ForegroundColor Green -NoNewline }
        "Failed" { Write-Host $status -ForegroundColor Red -NoNewline }
        "Cancelling" { Write-Host $status -ForegroundColor Magenta -NoNewline }
        "Cancelled" { Write-Host $status -ForegroundColor Magenta -NoNewline }
        default { Write-Host $status -ForegroundColor White -NoNewline }
    }
    
    Write-Host " | Progress: $percentage%" -NoNewline
    
    if ($reason) {
        Write-Host " | $reason" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
    
    # Exit if completed
    if ($status -in @("Successful", "Failed", "Cancelled")) {
        Write-Host "`nInstance refresh completed with status: $status" -ForegroundColor $(if ($status -eq "Successful") { "Green" } else { "Red" })
        
        if ($status -eq "Successful") {
            Write-Host "`nTesting endpoints..." -ForegroundColor Cyan
            $alb = "http://course-management-alb-dev-1530526851.us-east-1.elb.amazonaws.com"
            
            @("/health", "/courses", "/students", "/enrollments") | ForEach-Object {
                $endpoint = $_
                try {
                    $response = Invoke-WebRequest -Uri "$alb$endpoint" -UseBasicParsing -TimeoutSec 10
                    Write-Host "  $endpoint : " -NoNewline
                    Write-Host "[OK] $($response.StatusCode)" -ForegroundColor Green
                } catch {
                    Write-Host "  $endpoint : " -NoNewline
                    Write-Host "[FAIL] $($_.Exception.Message)" -ForegroundColor Red
                }
            }
        }
        break
    }
    
    Start-Sleep -Seconds $IntervalSeconds
}
