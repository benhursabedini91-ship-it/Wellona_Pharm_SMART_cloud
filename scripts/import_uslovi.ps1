# Import Supplier Excel Files to stg.pricefeed
# Wrapper script for bin/import_uslovi_excel.py

param(
    [string]$Supplier = "",
    [string]$DataDir = "",
    [switch]$Help
)

# Set UTF-8 encoding
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot
$SCRIPT_PATH = Join-Path $PROJECT_ROOT "bin\import_uslovi_excel.py"

if ($Help) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Import Supplier Excel Files → stg.pricefeed" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  .\import_uslovi.ps1                    # Import all suppliers"
    Write-Host "  .\import_uslovi.ps1 -Supplier PHOENIX  # Import specific supplier"
    Write-Host "  .\import_uslovi.ps1 -Help              # Show this help"
    Write-Host ""
    Write-Host "SUPPLIERS:" -ForegroundColor Yellow
    Write-Host "  PHOENIX, SOPHARMA, VEGA, FARMALOGIST"
    Write-Host ""
    Write-Host "EXCEL FILES:" -ForegroundColor Yellow
    Write-Host "  Place in: EB\UsloviDobavljaca\"
    Write-Host "    - Phoenix.xlsx"
    Write-Host "    - Sopharma.xlsx"
    Write-Host "    - Vega.xlsx"
    Write-Host "    - Farmalogist.xlsx"
    Write-Host ""
    Write-Host "DATABASE:" -ForegroundColor Yellow
    Write-Host "  Set environment variables:"
    Write-Host "    WPH_DB_HOST, WPH_DB_PORT, WPH_DB_NAME, WPH_DB_USER, WPH_DB_PASS"
    Write-Host ""
    exit 0
}

# Check if Python script exists
if (-not (Test-Path $SCRIPT_PATH)) {
    Write-Host "❌ Script not found: $SCRIPT_PATH" -ForegroundColor Red
    exit 1
}

# Check environment variables
if (-not $env:WPH_DB_NAME) {
    Write-Host "⚠️  WPH_DB_NAME not set, using default: wph_ai" -ForegroundColor Yellow
    $env:WPH_DB_NAME = "wph_ai"
}

if (-not $env:WPH_DB_HOST) {
    Write-Host "⚠️  WPH_DB_HOST not set, using default: localhost" -ForegroundColor Yellow
    $env:WPH_DB_HOST = "localhost"
}

if (-not $env:WPH_DB_USER) {
    Write-Host "⚠️  WPH_DB_USER not set, using default: postgres" -ForegroundColor Yellow
    $env:WPH_DB_USER = "postgres"
}

# Build Python command
$pythonArgs = @($SCRIPT_PATH)

if ($Supplier) {
    $pythonArgs += "--supplier", $Supplier
}

if ($DataDir) {
    $pythonArgs += "--data-dir", $DataDir
}

# Run Python script
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Running Import..." -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

& python @pythonArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✅ Import completed successfully" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  ❌ Import failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Red
}

exit $LASTEXITCODE
