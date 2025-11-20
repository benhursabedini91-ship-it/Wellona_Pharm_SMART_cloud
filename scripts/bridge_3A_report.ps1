param(
  [string]$ConfigPath = "C:\Wellona\wphAI\configs\bridge_3A.json"
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

# Support both schemas: nested config.pg15{} or flat at root
$cfg = $config.pg15
if (-not $cfg) { $cfg = $config }

$pgbin   = $cfg.bin.TrimEnd('\\')
$psql    = Join-Path $pgbin 'psql.exe'
$pgHost  = $cfg.host
$port    = [string]$cfg.port
$user    = $cfg.user
$dbWph   = $cfg.db_wph
$reportDir = $config.report_outdir

if (!(Test-Path $reportDir)) { New-Item -Path $reportDir -ItemType Directory | Out-Null }
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$outCsv = Join-Path $reportDir ("BRIDGE_3A_${ts}.csv")

# Build SQL to emit simple counts and max dates
$tblList = ($config.restore.tables | ForEach-Object { $_.Trim() })
$cntSql = @"
COPY (
SELECT 'eb_fdw' AS scope, rel, cnt, max_date FROM (
  SELECT 'artikli' AS rel, count(*)::bigint AS cnt, NULL::date AS max_date FROM eb_fdw.artikli
  UNION ALL
  SELECT 'komintenti', count(*)::bigint, NULL::date FROM eb_fdw.komintenti
  UNION ALL
  SELECT 'kalkopste', count(*)::bigint, NULL::date FROM eb_fdw.kalkopste
  UNION ALL
  SELECT 'kalkstavke', count(*)::bigint, NULL::date FROM eb_fdw.kalkstavke
) s
UNION ALL
SELECT 'wph_core' AS scope, 'mv_kalk' AS rel, count(*)::bigint AS cnt, max(datum)::date AS max_date FROM wph_core.mv_kalk
) TO STDOUT WITH CSV HEADER
"@

& $psql -h $pgHost -p $port -U $user -d $dbWph -v ON_ERROR_STOP=1 -c "$cntSql" > $outCsv

Write-Host "Report written: $outCsv" -ForegroundColor Green
