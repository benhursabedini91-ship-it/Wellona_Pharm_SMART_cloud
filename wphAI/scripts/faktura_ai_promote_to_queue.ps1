param(
  [string]$ConfigPath = "C:\Wellona\wphAI\configs\faktura_ai.json",
  [string]$RunDate = $(Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'

if (!(Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$inboxes = @($cfg.inboxes)

$outDay = Join-Path $cfg.outdir $RunDate
if (!(Test-Path $outDay)) { throw "Output folder not found: $outDay" }
$summary = Get-ChildItem -Path $outDay -Filter "FAKTURA_AI_SUMMARY_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $summary) { throw "Summary CSV not found in $outDay" }

$rows = Import-Csv -Path $summary.FullName
$clean = $rows | Where-Object { $_.status -eq 'CLEAN' }

$queueRoot = Join-Path "C:\Wellona\wphAI\queue\erp_import" $RunDate
New-Item -Path $queueRoot -ItemType Directory -Force | Out-Null

$queue = @()
foreach ($r in $clean) {
  $inv = $r.invoice_no
  if (-not $inv) { continue }
  $invId = ($inv -replace '/', '_')
  $found = $null
  foreach ($ib in $inboxes) {
    if (Test-Path $ib) {
      $cand = Get-ChildItem -Path $ib -Recurse -File -Include *.xml | Where-Object { $_.Name -like "*${invId}*.xml" } | Select-Object -First 1
      if ($cand) { $found = $cand; break }
    }
  }
  if (-not $found) { continue }
  $destName = "${invId}.xml"
  $dest = Join-Path $queueRoot $destName
  Copy-Item -Path $found.FullName -Destination $dest -Force
  $queue += [pscustomobject]@{
    invoice_no = $inv
    supplier   = $r.supplier
    src_xml    = $found.FullName
    dest_xml   = $dest
    items      = $r.items
    match_rate = $r.match_rate_pct
    total_calc = $r.total_calc
    total_hdr  = $r.total_header
  }
}

$qPath = Join-Path $queueRoot 'QUEUE.json'
$queue | ConvertTo-Json -Depth 4 | Out-File -FilePath $qPath -Encoding utf8

Write-Host ("Promoted {0} CLEAN invoices to queue: {1}" -f $queue.Count, $queueRoot) -ForegroundColor Green
