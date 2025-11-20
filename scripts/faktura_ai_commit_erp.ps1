param(
  [string]$UiConfig = "C:\Wellona\wphAI\configs\erp_ui.json",
  [string]$RunDate = $(Get-Date -Format 'yyyyMMdd')
)

function Convert-ShortcutToAhk {
  param([string]$shortcut)
  if ([string]::IsNullOrWhiteSpace($shortcut)) { return "" }
  $s = $shortcut.Trim()
  # Normalize common forms
  if ($s -match '^(?i)ALT\+([A-Z])$') { return "!" + ($Matches[1].ToLower()) }
  if ($s -match '^(?i)CTRL\+([A-Z])$') { return "^" + ($Matches[1].ToLower()) }
  if ($s -match '^(?i)SHIFT\+([A-Z])$') { return "+" + ($Matches[1].ToLower()) }
  if ($s -match '^(?i)ALT\+F(\d{1,2})$') { return "!{F$($Matches[1])}" }
  if ($s -match '^(?i)F(\d{1,2})$') { return "{F$($Matches[1])}" }
  # Already an AHK sequence like !k or {F9}
  return $s
}

$ErrorActionPreference = 'Stop'
if (!(Test-Path $UiConfig)) { throw "UI config not found: $UiConfig" }
$ui = Get-Content $UiConfig -Raw | ConvertFrom-Json

$queuePath = Join-Path "C:\Wellona\wphAI\queue\erp_import" $RunDate
if (!(Test-Path $queuePath)) { throw "Queue not found: $queuePath" }
$xmls = Get-ChildItem -Path $queuePath -Filter *.xml -File
if ($xmls.Count -eq 0) { Write-Host "Queue empty ($queuePath). Nothing to commit." -ForegroundColor Yellow; exit 0 }

# Find AutoHotkey
$ahkPaths = @(
  "C:\Program Files\AutoHotkey\AutoHotkey.exe",
  "C:\Program Files\AutoHotkey\v1\AutoHotkey.exe",
  "C:\Program Files\AutoHotkey\v2\AutoHotkey.exe"
)
$ahk = $ahkPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ahk) { throw "AutoHotkey not found. Please install AutoHotkey v1." }

$script = Join-Path $PSScriptRoot 'commit_erp.ahk'
if (!(Test-Path $script)) { throw "commit_erp.ahk missing at $script" }

Write-Host "[COMMIT] Starting ERP import (pilot) from $queuePath" -ForegroundColor Cyan

# Normalize shortcuts to AHK send syntax
$prokAhk = Convert-ShortcutToAhk $ui.proknjizi_alt
$preuzKeyAhk = Convert-ShortcutToAhk $ui.preuzmi_key

& $ahk `
  $script `
  $queuePath `
  $($ui.win_title) `
  $($ui.open_dialog_title) `
  $($ui.nav_mode) `
  $($ui.ctx_menu_index) `
  $preuzKeyAhk `
  $prokAhk `
  $($ui.exe_path) `
  $($ui.click_offsets.preuzmi.x) `
  $($ui.click_offsets.preuzmi.y) `
  $($ui.click_offsets.proknjizi.x) `
  $($ui.click_offsets.proknjizi.y) `
  $($ui.supplier_select.vendor_menu_index) `
  $($ui.supplier_select.vendor_key)

Write-Host "[PING_OK] ERP commit script executed" -ForegroundColor Green
