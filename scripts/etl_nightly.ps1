# Wellona SMART — Nightly ETL runner + backup
# Schedule via Task Scheduler (Windows) at 02:15 daily.

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8

$ROOT = "C:\Wellona\wphAI"
$SMART = "C:\Wellona\Wellona_Pharm_SMART"
$VENV = Join-Path $ROOT ".venv"
$PY = Join-Path $VENV "Scripts\python.exe"

if (-not (Test-Path $PY)) { Write-Error "Missing venv. Run scripts/setup.ps1"; exit 1 }

$env:WPH_APP_USE_DB = "1"
if (-not $env:WPH_DB_NAME) { $env:WPH_DB_NAME = "wph_ai_0262000" }

# Prefer orchestrator (DB-centric)
$Orchestrator = Join-Path $ROOT "bin\wph_ai_orchestrator.py"
$AppEtl = Join-Path $ROOT "app\etl_run.ps1"

try {
  if (Test-Path $Orchestrator) {
    & $PY $Orchestrator
  } elseif (Test-Path $AppEtl) {
    & $AppEtl
  } else {
    Write-Warning "No ETL entrypoint found. Skipping ETL run."
  }
}
catch {
  Write-Error "ETL failed: $_"
}

# Backup DB (pg_dump custom format)
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$bkDir = Join-Path $ROOT "backups"
if (-not (Test-Path $bkDir)) { New-Item -ItemType Directory -Force -Path $bkDir | Out-Null }
$dumpPath = Join-Path $bkDir "${env:WPH_DB_NAME}_$ts.dump"

try {
  psql -h $env:WPH_DB_HOST -p $env:WPH_DB_PORT -U $env:WPH_DB_USER -d $env:WPH_DB_NAME -c "select current_database();" | Out-Null
  pg_dump -h $env:WPH_DB_HOST -p $env:WPH_DB_PORT -U $env:WPH_DB_USER -d $env:WPH_DB_NAME -Fc -f $dumpPath
  Write-Host "Backup saved: $dumpPath" -ForegroundColor Green
} catch {
  Write-Warning "Backup failed: $_"
}
