# Apply sales_window feature + React UI (optional)
param([switch]$ReactUI)

$ErrorActionPreference = 'Stop'
Write-Host "Applying sales_window feature..." -ForegroundColor Cyan

# 1) Apply SQL patches
$psql = (Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter psql.exe | Select-Object -First 1).FullName
$env:PGPASSWORD = "0262000"

Write-Host "  → Creating sales MVs (7d, 30d)..."
& $psql -h 127.0.0.1 -U postgres -d wph_ai -f patches/sales_windows_7d_30d.sql | Out-Null

Write-Host "  → Restarting Flask server..."
$proc = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*wphAI*" }
if ($proc) { Stop-Process -Id $proc.Id -Force }
Start-Sleep -Seconds 2

Push-Location web_modern
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python app_v2.py" -WindowStyle Minimized
Pop-Location

Write-Host "`n✅ Done! Server restarted on http://127.0.0.1:8055" -ForegroundColor Green
Write-Host "   Test: http://127.0.0.1:8055/api/orders?target_days=6&sales_window=7" -ForegroundColor Yellow

if ($ReactUI) {
    Write-Host "`n�� React UI option: place order_brain_react.tsx in web_modern/public/" -ForegroundColor Cyan
    Write-Host "   Then build with Vite/Next.js or embed directly." -ForegroundColor Yellow
}

