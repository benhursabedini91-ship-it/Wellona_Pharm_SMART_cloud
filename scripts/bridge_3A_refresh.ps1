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

$pgbin   = $cfg.bin.TrimEnd('\\')
$psql    = Join-Path $pgbin 'psql.exe'
$pgHost  = $cfg.host
$port    = [string]$cfg.port
$user    = $cfg.user
$dbWph   = $cfg.db_wph
$targetDb= $cfg.db_restore_target

# Safety rails
if ($pgbin -notmatch 'PostgreSQL\\18\\bin') { throw "Safety guard: bin must be PG18 bin. Current: $pgbin" }
if ($pgHost -ne '127.0.0.1' -or $port -ne '5432') { $curr = "{0}:{1}" -f $pgHost, $port; throw "Safety guard: host/port must be 127.0.0.1:5432. Current: $curr" }
if ($dbWph -ne 'wph_ai') { throw "Safety guard: db_wph must be 'wph_ai'. Current: $dbWph" }
if ($targetDb -ne 'eb_core') { throw "Safety guard: db_restore_target must be 'eb_core'. Current: $targetDb" }

Write-Host "[REFRESH] host=$pgHost port=$port db_wph=$dbWph targetDb=$targetDb (DryRun=$DryRun)" -ForegroundColor Yellow
if ($DryRun) { Write-Host "Dry run only. Exiting before making changes." -ForegroundColor Cyan; return }

# Resolve password from env if present
${envPassVar} = $cfg.password_env
$envPassItem = $null
try { $envPassItem = Get-Item -Path "Env:${envPassVar}" -ErrorAction Stop } catch {}
$pgPass = $null
if ($envPassItem) { $pgPass = $envPassItem.Value }
${prevPwd} = $env:PGPASSWORD
if ($pgPass) { $env:PGPASSWORD = $pgPass }

# Build SQL to create FDW to the freshly restored '$targetDb' DB and import tables
$tblList = ($config.restore.tables | ForEach-Object { $_.Trim() }) -join ', '
$serverName = $config.fdw.server_name
$remoteSchema = $config.fdw.schema_remote
$localSchema  = $config.fdw.schema_local
$coreSchema   = $config.schemas.derived

$pwFragment = ''
if ($pgPass) { $pwFragment = ", password '$pgPass'" }

 # Phase 1: FDW setup and import
$sql1 = @"
CREATE SCHEMA IF NOT EXISTS ${localSchema};
CREATE SCHEMA IF NOT EXISTS ${coreSchema};
CREATE EXTENSION IF NOT EXISTS postgres_fdw;
DROP SERVER IF EXISTS ${serverName} CASCADE;
CREATE SERVER ${serverName}
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host '${pgHost}', dbname '${targetDb}', port '${port}');
DROP USER MAPPING IF EXISTS FOR CURRENT_USER SERVER ${serverName};
CREATE USER MAPPING FOR CURRENT_USER SERVER ${serverName}
  OPTIONS (user '${user}'${pwFragment});
DROP SCHEMA IF EXISTS ${localSchema} CASCADE;
CREATE SCHEMA ${localSchema};
IMPORT FOREIGN SCHEMA ${remoteSchema}
  LIMIT TO (${tblList})
  FROM SERVER ${serverName}
  INTO ${localSchema};
"@
& $psql -h $pgHost -p $port -U $user -d $dbWph -v ON_ERROR_STOP=1 -c "$sql1"

# Phase 2: Create MVs (tolerant)
$sql2 = @"
DROP MATERIALIZED VIEW IF EXISTS ${coreSchema}.mv_katalog;
CREATE MATERIALIZED VIEW ${coreSchema}.mv_katalog AS
SELECT a.sifra, a.barkod, a.naziv FROM ${localSchema}.artikli a;

DROP MATERIALIZED VIEW IF EXISTS ${coreSchema}.mv_kalk;
CREATE MATERIALIZED VIEW ${coreSchema}.mv_kalk AS
SELECT h.id::bigint AS kalk_id,
       h.broj::text AS invoice_no,
       h.datum::date AS datum,
       i.artikal::text AS sifra,
       i.kolicina::numeric AS kolicina,
       i.nabavnacena::numeric AS vpc,
       i.rabatstopa::numeric AS rabat,
       i.pdvstopa::numeric AS pdv
FROM ${localSchema}.kalkopste h
JOIN ${localSchema}.kalkstavke i ON i.kalkid = h.id;

CREATE INDEX IF NOT EXISTS mv_kalk_idx ON ${coreSchema}.mv_kalk(invoice_no);
REFRESH MATERIALIZED VIEW ${coreSchema}.mv_katalog;
REFRESH MATERIALIZED VIEW ${coreSchema}.mv_kalk;
"@
& $psql -h $pgHost -p $port -U $user -d $dbWph -v ON_ERROR_STOP=1 -c "$sql2"

# restore PGPASSWORD
$env:PGPASSWORD = ${prevPwd}

Write-Host "FDW linked and MVs refreshed in DB '$dbWph'." -ForegroundColor Green
