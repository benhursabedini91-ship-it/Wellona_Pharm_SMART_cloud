#requires -Version 5.1
# Wellona SMART — Local setup bootstrap (Windows PowerShell)
# Purpose: one-time setup. Creates venv, installs dependencies, sets env vars.
# Usage: Right-click -> Run with PowerShell OR run: powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8

Write-Host "== Wellona SMART • Local Setup ==" -ForegroundColor Cyan

# Paths (absolute, Windows-first)
$ROOT = "C:\Wellona\wphAI"
$SMART = "C:\Wellona\Wellona_Pharm_SMART"
$VENV = Join-Path $ROOT ".venv"
$PY = Join-Path $VENV "Scripts\python.exe"

# Ensure Python is available
$pythonOk = $false
try { python --version | Out-Null; $pythonOk = $true } catch {}
if (-not $pythonOk) {
  Write-Host "Python not found in PATH. Please install Python 3.10+ and retry." -ForegroundColor Red
  exit 1
}

# Create venv if missing
if (-not (Test-Path $VENV)) {
  Write-Host "Creating virtual environment at $VENV" -ForegroundColor Yellow
  python -m venv $VENV
}

# Upgrade pip + core tools
& $PY -m pip install --upgrade pip wheel setuptools

# Consolidated dependencies (backend + fiskal + ETL)
$deps = @(
  'flask','waitress','requests','pandas','openpyxl','python-dateutil','psycopg2-binary','gunicorn','python-dotenv'
)
Write-Host "Installing deps: $($deps -join ', ')" -ForegroundColor Yellow
& $PY -m pip install $deps

# Optional: install app-specific requirements.txt if present
$req1 = Join-Path $SMART "wphAI\app\requirements.txt"
$req2 = Join-Path $ROOT "app\requirements.txt"
foreach ($req in @($req1,$req2)) {
  if (Test-Path $req) {
    Write-Host "Installing requirements from $req" -ForegroundColor Yellow
    & $PY -m pip install -r $req
  }
}

# Default environment (can be overridden per-session)
$env:APP_PORT = "8056"
$env:WPH_APP_USE_DB = "0"  # set to 1 when PostgreSQL is ready
$env:WPH_DB_HOST = "127.0.0.1"
$env:WPH_DB_PORT = "5432"
$env:WPH_DB_NAME = "wph_ai_0262000"
$env:WPH_DB_USER = "wph_ai"
$env:WPH_DB_PASS = "ChangeMeStrong!"

Write-Host "Environment primed. To persist globally, set System Environment Variables from Windows UI." -ForegroundColor Green

# Quick Postgres sanity (only if DB mode requested)
if ($env:WPH_APP_USE_DB -eq '1') {
  Write-Host "Checking PostgreSQL connectivity..." -ForegroundColor Yellow
  try {
    psql -h $env:WPH_DB_HOST -p $env:WPH_DB_PORT -U $env:WPH_DB_USER -d $env:WPH_DB_NAME -c "select current_database(), now();" | Out-Null
    Write-Host "PostgreSQL OK" -ForegroundColor Green
  } catch {
    Write-Warning "PostgreSQL check failed. Keep WPH_APP_USE_DB=0 until DB is available."
  }
}

Write-Host "Setup complete. Next: .\\scripts\\run_all.ps1" -ForegroundColor Cyan
