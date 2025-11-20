# eFaktura Daily Subscription Renewal
# Run this script daily via Task Scheduler

$ErrorActionPreference = "Stop"

# Set API key
$env:WPH_EFAKT_API_KEY = "f7b40af0-9689-4872-8d59-4779f7961175"

# Change to script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Run subscription
Write-Host "=== eFaktura Daily Subscription ===" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

python -c "from efaktura_webhook import subscribe_for_notifications; subscribe_for_notifications()"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Subscription renewed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Subscription failed" -ForegroundColor Red
    exit 1
}
