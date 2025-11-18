param(
    [string]$DbHost = "127.0.0.1",
    [int]$DbPort = 5432,  # fix: add missing comma
    [string]$DbUser = "postgres",
    [string]$DbName = "wph_ai"
)

$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$root   = Split-Path -Parent $root         # …\wphAI
$inDir  = Join-Path $root 'in\phoenix'
$stgDir = Join-Path $root 'staging'
$outDir = Join-Path $root 'out\orders'
$mapDir = Join-Path $root 'configs\mappers'

$null = New-Item -Type Directory -Force -Path $inDir,$stgDir,$outDir | Out-Null

function Say([string]$m,[ConsoleColor]$c='Gray'){ $t=(Get-Date).ToString('HH:mm:ss'); Write-Host "[$t] $m" -ForegroundColor $c }
function Psql([string]$sql){
  $exe = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
  # Ensure PGPASSWORD exists (prompt once if missing)
  if (-not $env:PGPASSWORD) {
    $sec = Read-Host "Postgres password" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
      [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    )
  }
  & $exe -h $DbHost -p $DbPort -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -c $sql 2>&1
}

# 1) Merr pipeline JSON (do e përdorim vetëm si kontroll)
$pipelineJson = Psql "SELECT wph_core.run_pipeline('nightly_etl');" | Out-String

# Log the pipeline result
if ($pipelineJson) {
    Write-Host "Pipeline execution result:" -ForegroundColor Green
    Write-Host $pipelineJson
} else {
    Write-Error "Pipeline execution failed or returned no result"
    exit 1
}

# 2) Ngarko mapper-in PHOENIX@v1
$mapPath = Join-Path $mapDir 'phoenix_v1.json'
if(!(Test-Path $mapPath)){ throw "Mapper $mapPath nuk u gjet." }
$mapper = Get-Content $mapPath -Raw | ConvertFrom-Json
$hdr = [int]$mapper.input.hdr
$ixB = [int]$mapper.input.barcode
$ixP = [int]$mapper.input.vpc
$ixK = [int]$mapper.input.kasa_plus

# 3) Kthe .xlsx -> .csv nëse duhet
function Convert-XlsxToCsv([string]$xlsx){
  try{
    $xl = New-Object -ComObject Excel.Application
    $xl.Visible = $false
    $wb = $xl.Workbooks.Open($xlsx)
    $csv = [System.IO.Path]::ChangeExtension($xlsx,'csv')
    $wb.SaveAs($csv,6); $wb.Close($true); $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb)|Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl)|Out-Null
    return $csv
  } catch {
    throw "Konvertimi XLSX->CSV dështoi për $xlsx. $_"
  }
}

# 4) Përgatit tabelën stg
$ddl = @"
CREATE SCHEMA IF NOT EXISTS stg AUTHORIZATION postgres;
CREATE TABLE IF NOT EXISTS stg.phoenix(
  src_file    text,
  row_no      int,
  barcode     text,
  vpc         numeric,
  kasa_plus   numeric
);
TRUNCATE stg.phoenix;
"@
Psql $ddl | Out-Null

# 5) Lexo file-t, filtro, dhe ngarko
$files = Get-ChildItem $inDir -File -Include *.xlsx,*.csv
if($files.Count -eq 0){ Say "S'u gjetën file te $inDir. Vendos *.xlsx ose *.csv." Yellow; exit 0 }

$banned = @("IGLA","IGLE","SPRIC","RUKAVICA","RUKAVICE","CONTOUR PLUS","MASKE","MASKA")

$tempCsv = Join-Path $stgDir ("phoenix_import_{0:yyyyMMdd_HHmmss}.csv" -f (Get-Date))
"src_file,row_no,barcode,vpc,kasa_plus" | Out-File -Encoding UTF8 $tempCsv

foreach($f in $files){
  $csv = if($f.Extension -ieq '.xlsx'){ Convert-XlsxToCsv $f.FullName } else { $f.FullName }
  $i=0
  Get-Content $csv | ForEach-Object {
    $i++
    if($i -le $hdr){ return } # skip header-at deri tek $hdr
    $parts = $_.Split(',')  # thjeshtë; nëse ke CSV me presje brenda fushave do e forcojmë me parser tjetër
    if($parts.Count -lt [Math]::Max($ixB,$ixP,$ixK)){ return }
    $barcode = $parts[$ixB-1].Trim('"')
    $vpc     = $parts[$ixP-1].Trim('"') -as [decimal]
    $kasa    = $parts[$ixK-1].Trim('"') -as [decimal]
    # Validime të thjeshta:
    if([string]::IsNullOrWhiteSpace($barcode)){ return }
    if($vpc -le 0){ return }
    $lineUpper = $_.ToUpperInvariant()
    if($banned | Where-Object { $lineUpper.Contains($_) }){ return }
    "$($f.Name),$i,$barcode,$vpc,$kasa" | Add-Content -Encoding UTF8 $tempCsv
  }
}

# 6) COPY -> stg.phoenix
Psql "\copy stg.phoenix FROM '$tempCsv' WITH (FORMAT csv, HEADER true)" | Out-Null
Say "U ngarkuan të dhënat në stg.phoenix." Green

# 7) Emit provizor -> out\orders\orders_{ts}.csv
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$outFile = Join-Path $outDir "orders_$ts.csv"
# për demo: eksportojmë qetë ashtu siç janë
$exportSql = "\copy (SELECT barcode, vpc, COALESCE(kasa_plus,0) AS kasa_plus FROM stg.phoenix) TO '$outFile' WITH (FORMAT csv, HEADER true)"
Psql $exportSql | Out-Null
Say "U krijua: $outFile" Green

Say "[PING_OK] ETL i kryer." Green
