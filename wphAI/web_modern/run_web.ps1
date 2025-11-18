# C:\Wellona\wphAI\web_modern\run_web.ps1
param(
  [int]$Port = 8055
)

$ErrorActionPreference = "Stop"
Write-Host "[RUN] Starting Wellona Web on port $Port..."

# Mbyll python të vjetër po të ketë
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue | Out-Null

# Kalo në folderin e app-it
Set-Location "C:\Wellona\wphAI\web_modern"

# Nise app-in pa reloader e pa debug
python -c "from app_v2 import app; app.run(host='127.0.0.1', port=$Port, debug=False, use_reloader=False)"
