param(
  [string]$DbHost='127.0.0.1',
  [int]$DbPort=5432,
  [string]$DbName='wph_ai',
  [string]$DbUser='postgres'
)

# --- Helpers ---
function Write-Stamp($msg,[ConsoleColor]$c='Gray'){ $t=(Get-Date).ToString('HH:mm:ss'); Write-Host "[$t] $msg" -ForegroundColor $c }
function Psql([string]$sql){
  if (-not $env:PGPASSWORD) {
    $sec = Read-Host "Postgres password" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
      [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    )
  }
  $exe = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
  & $exe -h $DbHost -p $DbPort -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -c $sql 2>&1
}

function Ensure-Folders{
  $paths = @(
    "$env:ROOT\in\phoenix",
    "$env:ROOT\staging",
    "$env:ROOT\out\orders",
    "$env:ROOT\logs",
    "$env:ROOT\configs\mappers",
    "$env:ROOT\configs\pipelines"
  )
  foreach($p in $paths){ New-Item -Type Directory -Force -Path $p | Out-Null }
  Write-Stamp "Struktura e dosjeve është gati." Green
}

function Seed-Configs {
  $mapper = @{
    supplier = "PHOENIX"
    input    = @{ hdr=19; barcode=8; vpc=14; kasa_plus=19; coef=100 }
    id_rules = @{ banned_words = @("IGLA","IGLE","SPRIC","RUKAVICA","RUKAVICE","CONTOUR PLUS","MASKE","MASKA"); price_gt = 0 }
  } | ConvertTo-Json -Depth 6
  $pipeline = @{
    steps = @(
      @{ id="import_phoenix"; type="load_xlsx"; input="$env:ROOT/in/phoenix/*.xlsx"; mapper="PHOENIX@v1"; staging="stg.phoenix" },
      @{ id="validate"; type="validate"; rules=@("banned_words","price>0") },
      @{ id="choose_supplier"; type="map"; logic="best_price_with_filters" },
      @{ id="export_orders"; type="emit"; dest="$env:ROOT/out/orders/" },
      @{ id="log"; type="log_run" }
    )
  } | ConvertTo-Json -Depth 6

  $mPath = "$env:ROOT\configs\mappers\phoenix_v1.json"
  $pPath = "$env:ROOT\configs\pipelines\nightly_etl.json"
  if(-not (Test-Path $mPath)){ $mapper | Out-File -Encoding UTF8 $mPath }
  if(-not (Test-Path $pPath)){ $pipeline | Out-File -Encoding UTF8 $pPath }
  Write-Stamp "Mapper & pipeline seed u siguruan." Green
}

function Verify-System {
  Write-Stamp "Verifikim i sistemit…" Cyan
  $q1 = "SELECT schema_name FROM information_schema.schemata ORDER BY 1;"
  $q2 = "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema IN ('wph_core','audit') ORDER BY 1,2;"
  $q3 = "SELECT n.nspname AS schema, p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='wph_core' ORDER BY 2;"
  $q4 = "SELECT pipeline_code,is_active FROM wph_core.pipelines;"
  Psql $q1 | Out-Host
  Psql $q2 | Out-Host
  Psql $q3 | Out-Host
  Psql $q4 | Out-Host
  Write-Stamp "[PING_OK] Verifikimi përfundoi." Green
}

function Run-Nightly {
  Write-Stamp "Thirrje: wph_core.run_pipeline('nightly_etl')" Cyan
  Psql "SELECT wph_core.run_pipeline('nightly_etl');" | Out-Host
  Write-Stamp "[PING_OK] Pipeline u ekzekutua." Green
}

function Show-Audit {
  Psql "SELECT event_id,event_time,actor,action FROM audit.events ORDER BY event_id DESC LIMIT 20;" | Out-Host
}

# --- Main ---
$env:ROOT = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
Ensure-Folders
Seed-Configs
Verify-System

while($true){
  Write-Host ""
  Write-Host "===== Wellona • WPH_AI App =====" -ForegroundColor Yellow
  Write-Host "1) Run pipeline tani"
  Write-Host "2) Shfaq audit 20 të fundit"
  Write-Host "3) Rishiko sistemin / status"
  Write-Host "4) Hap folderin e porosive (out\orders)"
  Write-Host "0) Dil"
  $c = Read-Host "Zgjedhja"
  switch($c){
    '1' { Run-Nightly }
    '2' { Show-Audit }
    '3' { Verify-System }
    '4' { ii "$env:ROOT\out\orders" }
    '0' { break }
    default { Write-Stamp "Zgjedhje e panjohur." Red }
  }
}
