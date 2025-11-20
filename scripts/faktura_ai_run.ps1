param(
  [string]$ConfigPath = "C:\Wellona\wphAI\configs\faktura_ai.json"
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $PSScriptRoot
$py = 'python'
$env:PYTHONIOENCODING = 'utf-8'

Write-Host "[FAKTURA_AI] Starting MVP parse  drafts" -ForegroundColor Cyan
& $py "$base\app\faktura_ai_mvp.py"
Write-Host "[PING_OK] FAKTURA_AI MVP completed" -ForegroundColor Green
