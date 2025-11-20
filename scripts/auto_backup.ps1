[CmdletBinding()]
param(
    [string]$OutDir = "C:\Wellona\wphAI\backups",
    [int]$Retention = 10,
    [switch]$NoManifest
)

<#
Purpose: Create timestamped ZIP backup + (optionally) a manifest of file hashes.
Usage:
  powershell -File scripts\auto_backup.ps1
  powershell -File scripts\auto_backup.ps1 -OutDir D:\safe_backups -Retention 20

Manifest format (MD5):
  <hash> *relative\path

Exclusions: large transient/output dirs are skipped.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function New-Dir($path){ if(-not (Test-Path $path)){ New-Item -ItemType Directory -Path $path | Out-Null } }
New-Dir $OutDir

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$zipName   = "wphAI_backup_$timestamp.zip"
$zipPath   = Join-Path $OutDir $zipName
$manifest  = Join-Path $OutDir "wphAI_manifest_$timestamp.txt"

# Root project path
$root = "C:\Wellona\wphAI"

# Paths to include (code + config). Adjust as needed.
$include = @(
    'app','web_modern','scripts','configs','bin','sql','docs','wph_ai_mcp_server.py','app_v2.py','README.md'
) | ForEach-Object { Join-Path $root $_ }

# Transient/excluded directories
$excludeDirs = @('staging','logs','out','in','backups','__pycache__','queue','archive','data','tests','wphAI-feature-include-zero-wip','wphAI-main')

# Build file list manually to allow exclusions.
Write-Host "Collecting files..." -ForegroundColor Cyan
$files = foreach($path in $include){
    if(Test-Path $path){
        if((Get-Item $path).PSIsContainer){
            Get-ChildItem $path -Recurse -File | Where-Object {
                $rel = $_.FullName.Substring($root.Length).TrimStart('\\')
                $excludeDirs -notcontains ($rel.Split('\\')[0])
            }
        } else { Get-Item $path }
    }
}

if(-not $files){ Write-Warning 'No files collected for backup.'; exit 1 }

# Create a staging temp folder
$temp = Join-Path $OutDir "__tmp_$timestamp"
New-Dir $temp

foreach($f in $files){
    $rel = $f.FullName.Substring($root.Length).TrimStart('\\')
    $dest = Join-Path $temp $rel
    New-Dir (Split-Path $dest -Parent)
    Copy-Item $f.FullName $dest -Force
}

Write-Host "Compressing $($files.Count) files -> $zipPath" -ForegroundColor Yellow
Compress-Archive -Path (Join-Path $temp '*') -DestinationPath $zipPath -CompressionLevel Optimal

if(-not $NoManifest){
    Write-Host "Generating manifest..." -ForegroundColor Yellow
    $hashLines = foreach($f in Get-ChildItem $temp -Recurse -File){
        $rel = $f.FullName.Substring($temp.Length).TrimStart('\\')
        $md5 = (Get-FileHash $f.FullName -Algorithm MD5).Hash.ToLower()
        "$md5 *$rel"
    }
    $hashLines | Set-Content -Encoding UTF8 $manifest
}

# Cleanup temp
Remove-Item $temp -Recurse -Force

# Retention
$existing = Get-ChildItem $OutDir -File -Filter 'wphAI_backup_*.zip' | Sort-Object LastWriteTime -Descending
if($existing.Count -gt $Retention){
    $toRemove = $existing | Select-Object -Skip $Retention
    foreach($old in $toRemove){
        Write-Host "Removing old backup: $($old.Name)" -ForegroundColor DarkGray
        Remove-Item $old.FullName -Force
        $mf = $old.FullName -replace 'wphAI_backup_','wphAI_manifest_' -replace '.zip','.txt'
        if(Test-Path $mf){ Remove-Item $mf -Force }
    }
}

Write-Host "Backup complete:" -ForegroundColor Green
Write-Host " ZIP: $zipPath" -ForegroundColor Green
if(-not $NoManifest){ Write-Host " Manifest: $manifest" -ForegroundColor Green }
