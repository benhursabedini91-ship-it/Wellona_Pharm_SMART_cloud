# Run Fiscal Bills Web UI
# Starter script për Web Dashboard

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== Fiscal Bills Web UI ===" -ForegroundColor Cyan

# Check API key
if (-not $env:WPH_EFAKT_API_KEY) {
    Write-Host "WARNING: WPH_EFAKT_API_KEY not set!" -ForegroundColor Yellow
    Write-Host "Set it with: `$env:WPH_EFAKT_API_KEY='your_key'" -ForegroundColor Yellow
}

# Default port
if (-not $env:FISCAL_WEB_PORT) {
    $env:FISCAL_WEB_PORT = "5556"
}

Write-Host "Starting web server on port $env:FISCAL_WEB_PORT ..." -ForegroundColor Green

# Run Flask app
python "$PSScriptRoot\fiscal_web.py"
