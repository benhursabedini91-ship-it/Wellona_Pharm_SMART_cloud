param(
  [string]$ConfigPath = "C:\Wellona\wphAI\configs\bridge_3A.json"
)

$ErrorActionPreference = 'Stop'
Write-Host "[BRIDGE_3A] Nightly run started $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan

try {
  & "$PSScriptRoot\bridge_3A_restore.ps1" -ConfigPath $ConfigPath
  & "$PSScriptRoot\bridge_3A_refresh.ps1" -ConfigPath $ConfigPath
  & "$PSScriptRoot\bridge_3A_report.ps1" -ConfigPath $ConfigPath
  Write-Host "[PING_OK] Bridge 3A completed successfully $(Get-Date -Format 'u')" -ForegroundColor Green
}
catch {
  Write-Host "[INCIDENT] Bridge 3A failed: $($_.Exception.Message)" -ForegroundColor Red
  throw
}
