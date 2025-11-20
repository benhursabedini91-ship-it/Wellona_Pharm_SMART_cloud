param(
  [string]$ConfigPath = "C:\Wellona\wphAI\configs\bridge_3A.json",
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

# Support both schemas: nested config.pg15{} or flat at root
$cfg = $config.pg15
if (-not $cfg) { $cfg = $config }

# Resolve PGPASSWORD from env
${envPassVar} = $cfg.password_env
$envPassItem = $null
try { $envPassItem = Get-Item -Path "Env:${envPassVar}" -ErrorAction Stop } catch {}
if (-not $envPassItem) {
  Write-Host "WARNING: Env var '$(${envPassVar})' not set. pg_restore may prompt for password." -ForegroundColor Yellow
}

$pgbin   = $cfg.bin.TrimEnd('\\')
$psql    = Join-Path $pgbin 'psql.exe'
$pgrest  = Join-Path $pgbin 'pg_restore.exe'
$pgHost  = $cfg.host
$port    = [string]$cfg.port
$user    = $cfg.user
$targetDb= $cfg.db_restore_target

# Safety rails: do NOT touch ERP/9.3. Only allow PG18 local defaults.
if ($pgbin -notmatch 'PostgreSQL\\18\\bin') {
  throw "Safety guard: bin path must point to PostgreSQL 18 bin. Current: $pgbin"
}
if ($pgHost -ne '127.0.0.1' -or $port -ne '5432') {
  $curr = "{0}:{1}" -f $pgHost, $port
  throw "Safety guard: host/port must be 127.0.0.1:5432 (PG18). Current: $curr"
}
if ($targetDb -ne 'eb_core') {
  throw "Safety guard: db_restore_target must be 'eb_core'. Current: $targetDb"
}

Write-Host "[RESTORE] PG18 bin=$pgbin host=$pgHost port=$port targetDb=$targetDb (DryRun=$DryRun)" -ForegroundColor Yellow
if ($DryRun) { Write-Host "Dry run only. Exiting before making changes." -ForegroundColor Cyan; return }

# Find latest backup file (*.backup)
$backup = $null
$searchPaths = @($config.backup_search_paths)
foreach ($base in $searchPaths) {
  if (Test-Path $base) {
    $cand = Get-ChildItem -Path $base -Recurse -File -Include *.backup | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($cand) { $backup = $cand.FullName; break }
  }
}
if (-not $backup) { throw "No .backup file found in: $($config.backup_search_paths -join '; ')" }

Write-Host "Using backup: $backup" -ForegroundColor Cyan

## Drop + create target DB cleanly (run in separate calls to avoid transaction block)
$prev = $env:PGPASSWORD
if ($envPassItem) { $env:PGPASSWORD = $envPassItem.Value }
# terminate connections
& $psql -h $pgHost -p $port -U $user -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$targetDb';"
# conditional drop with safe formatting
$dropSql   = ("DO $$BEGIN IF EXISTS (SELECT 1 FROM pg_database WHERE datname = '{0}') THEN EXECUTE 'DROP DATABASE ""{0}""'; END IF; END$$;" -f $targetDb)
& $psql -h $pgHost -p $port -U $user -d postgres -v ON_ERROR_STOP=1 -c $dropSql
# create fresh db
$createSql = ("CREATE DATABASE ""{0}"" WITH ENCODING 'UTF8' TEMPLATE template0;" -f $targetDb)
& $psql -h $pgHost -p $port -U $user -d postgres -v ON_ERROR_STOP=1 -c $createSql

# Build pg_restore args
$restoreArgs = @('-h', $pgHost, '-p', $port, '-U', $user, '-d', $targetDb, '--no-owner', '--clean', '--if-exists', '--verbose')

if ($config.restore.mode -eq 'tables' -and $config.restore.tables.Count -gt 0) {
  foreach ($t in $config.restore.tables) { $restoreArgs += @('-t', $t) }
}
$restoreArgs += $backup

Write-Host "Running pg_restore → $targetDb" -ForegroundColor Green
# Set PGPASSWORD is already set above for psql; reuse for pg_restore
& $pgrest @restoreArgs
# Clear PGPASSWORD
$env:PGPASSWORD = $prev

Write-Host "Restore complete." -ForegroundColor Green
