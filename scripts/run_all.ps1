#requires -Version 5.1
# Wellona SMART — One-command runner (Windows PowerShell)
# Starts the backend (port 8056) and Fiskal helper, opens UI.
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\run_all.ps1

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8

$ROOT = "C:\Wellona\wphAI"
$SMART = "C:\Wellona\Wellona_Pharm_SMART"
$VENV = Join-Path $ROOT ".venv"
$PY = Join-Path $VENV "Scripts\python.exe"

if (-not (Test-Path $PY)) {
  Write-Host "Virtualenv not found. Run .\\scripts\\setup.ps1 first." -ForegroundColor Red
  exit 1
}

# Defaults (override via Environment Variables before running)
if (-not $env:APP_PORT) { $env:APP_PORT = "8056" }
if (-not $env:WPH_APP_USE_DB) { $env:WPH_APP_USE_DB = "0" }

Write-Host "== Starting services (DB=$($env:WPH_APP_USE_DB)) ==" -ForegroundColor Cyan

# Backend (Flask app_v2.py)
$BackendPath = Join-Path $SMART "WPH_EFaktura_Package\backend\app_v2.py"
if (-not (Test-Path $BackendPath)) {
  Write-Host "Backend app not found at $BackendPath" -ForegroundColor Red
  exit 1
}

# Fiskal helper
$FiskalPath = Join-Path $SMART "app\fiscal_web.py"
if (-not (Test-Path $FiskalPath)) {
  Write-Warning "Fiskal helper not found at $FiskalPath. Skipping..."
}

# Start backend
$backendArgs = @($BackendPath)
$backend = Start-Process -FilePath $PY -ArgumentList $backendArgs -PassThru -WindowStyle Minimized
Write-Host "Backend PID: $($backend.Id) → http://localhost:$($env:APP_PORT)/ui" -ForegroundColor Green

# Start fiskal (optional)
if (Test-Path $FiskalPath) {
  $fiskal = Start-Process -FilePath $PY -ArgumentList $FiskalPath -PassThru -WindowStyle Minimized
  Write-Host "Fiskal PID: $($fiskal.Id) → http://localhost:5556/" -ForegroundColor Green
}

# Open UI
Start-Process "http://localhost:$($env:APP_PORT)/ui"

Write-Host "Press Ctrl+C in child consoles to stop. Use Task Manager if needed." -ForegroundColor Yellow
