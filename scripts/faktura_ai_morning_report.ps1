param(
  [string]$ConfigPath = "C:\Wellona\wphAI\configs\faktura_ai.json",
  [string]$RunDate = $(Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'
if (!(Test-Path $ConfigPath)) { throw "Config not found: $ConfigPath" }
$cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
$outDay = Join-Path $cfg.outdir $RunDate
if (!(Test-Path $outDay)) { throw "Output folder not found: $outDay" }
$summary = Get-ChildItem -Path $outDay -Filter "FAKTURA_AI_SUMMARY_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $summary) { throw "Summary CSV not found in $outDay" }

$rows = Import-Csv -Path $summary.FullName
$clean = @($rows | Where-Object { $_.status -eq 'CLEAN' })
$review = @($rows | Where-Object { $_.status -eq 'NEEDS_REVIEW' })
$err = @($rows | Where-Object { $_.status -eq 'ERR' })

$txt = @()
$txt += "FAKTURA_AI – Morning Report $RunDate"
$txt += "Summary file: $($summary.FullName)"
$txt += "CLEAN: $($clean.Count) | REVIEW: $($review.Count) | ERR: $($err.Count)"
$txt += ""
if ($clean.Count -gt 0) {
  $txt += "CLEAN invoices:"
  $txt += ($clean | Select-Object invoice_no, supplier, items, match_rate_pct | Format-Table -AutoSize | Out-String)
}
if ($review.Count -gt 0) {
  $txt += "NEEDS_REVIEW:"
  $txt += ($review | Select-Object invoice_no, supplier, reason | Format-Table -AutoSize | Out-String)
}

$repTxt = Join-Path $outDay ("FAKTURA_AI_MORNING_${RunDate}.txt")
$txt -join "`r`n" | Out-File -FilePath $repTxt -Encoding utf8
Write-Host "Morning report written: $repTxt" -ForegroundColor Green
