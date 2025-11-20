# setup_efaktura.ps1
# Setup script për konfigurimin e eFaktura API credentials

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "  eFAKTURA API SETUP" -ForegroundColor Yellow
Write-Host "  Wellona Pharm SMART System" -ForegroundColor Gray
Write-Host ("=" * 80) -ForegroundColor Cyan

Write-Host "`n📋 Ky script do të konfigurojë credentials për eFaktura API" -ForegroundColor White
Write-Host ""

# Check if already configured
$existing_key = $env:WPH_EFAKT_API_KEY
if ($existing_key) {
    Write-Host "⚠️  API Key ekziston tashmë: $($existing_key.Substring(0, [Math]::Min(10, $existing_key.Length)))..." -ForegroundColor Yellow
    $overwrite = Read-Host "Dëshiron ta mbishkruash? (y/N)"
    if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
        Write-Host "✓ Setup anuluar. Duke përdorur konfigurimin ekzistues." -ForegroundColor Green
        exit 0
    }
}

Write-Host "`n🔑 Hapi 1: API Key" -ForegroundColor Cyan
Write-Host "   Merr API key nga: https://efaktura.mfin.gov.rs" -ForegroundColor Gray
Write-Host "   (Llogaria > API Access > Generate Key)" -ForegroundColor Gray
$api_key = Read-Host "`nVendos API Key"

if (-not $api_key) {
    Write-Host "❌ API Key është i detyrueshëm!" -ForegroundColor Red
    exit 1
}

Write-Host "`n🌐 Hapi 2: API Endpoints" -ForegroundColor Cyan
Write-Host "   Nëse nuk di URL-të e sakta, shtyp ENTER për default" -ForegroundColor Gray

$default_base = "https://efaktura.mfin.gov.rs"
$api_base = Read-Host "`nBase URL (Enter për default: $default_base)"
if (-not $api_base) {
    $api_base = $default_base
}

$default_list = "$api_base/api/publicApi/purchase-invoice/ids"
Write-Host "`nDefault LIST URL (POST): $default_list" -ForegroundColor Gray
$list_url = Read-Host "LIST URL (Enter për default)"
if (-not $list_url) {
    $list_url = $default_list
}

$default_get = "$api_base/api/publicApi/purchase-invoice/xml"
Write-Host "`nDefault GET XML URL: $default_get" -ForegroundColor Gray
$get_url = Read-Host "GET XML URL (Enter për default)"
if (-not $get_url) {
    $get_url = $default_get
}

Write-Host "`n💾 Hapi 3: Database Configuration (opsionale)" -ForegroundColor Cyan
Write-Host "   Për auto-import në ERP. Shtyp ENTER për të kaluar." -ForegroundColor Gray

$db_host = Read-Host "`nDB Host (Enter për 127.0.0.1)"
if (-not $db_host) { $db_host = "127.0.0.1" }

$db_port = Read-Host "DB Port (Enter për 5432)"
if (-not $db_port) { $db_port = "5432" }

$db_name = Read-Host "DB Name (Enter për wph_ai)"
if (-not $db_name) { $db_name = "wph_ai" }

$db_user = Read-Host "DB User (Enter për postgres)"
if (-not $db_user) { $db_user = "postgres" }

$db_pass = Read-Host "DB Password (Enter për të kaluar)" -AsSecureString
$db_pass_plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($db_pass)
)

Write-Host "`n⚙️  Hapi 4: Opsione të avancuara" -ForegroundColor Cyan

$write_remote = Read-Host "Lejo shkrim në DB remote? (y/N)"
$write_remote_val = if ($write_remote -eq 'y' -or $write_remote -eq 'Y') { "1" } else { "0" }

$auto_create = Read-Host "Lejo krijim automatik të artikujve? (y/N)"
$auto_create_val = if ($auto_create -eq 'y' -or $auto_create -eq 'Y') { "1" } else { "0" }

# Save to environment (current session)
Write-Host "`n💾 Duke ruajtur konfigurimin..." -ForegroundColor Cyan

$env:WPH_EFAKT_API_KEY = $api_key
$env:WPH_EFAKT_API_BASE = $api_base
$env:WPH_EFAKT_LIST_URL = $list_url
$env:WPH_EFAKT_GET_XML_URL = $get_url
$env:WPH_DB_HOST = $db_host
$env:WPH_DB_PORT = $db_port
$env:WPH_DB_NAME = $db_name
$env:WPH_DB_USER = $db_user
if ($db_pass_plain) {
    $env:WPH_DB_PASS = $db_pass_plain
}
$env:WPH_WRITE_REMOTE = $write_remote_val
$env:WPH_ALLOW_AUTO_CREATE = $auto_create_val

Write-Host "✓ Konfigurimi u ruajt (sesioni aktual)" -ForegroundColor Green

# Offer to save permanently
Write-Host "`n📝 Dëshiron ta ruash konfigurimin në .env file?" -ForegroundColor Yellow
Write-Host "   (Rekomandohet për përdorim të përsëritur)" -ForegroundColor Gray
$save_file = Read-Host "Ruaj në .env? (Y/n)"

if ($save_file -ne 'n' -and $save_file -ne 'N') {
    $env_path = Join-Path $PSScriptRoot ".env"
    
    $env_content = @"
# eFaktura API Configuration
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# API Credentials
WPH_EFAKT_API_KEY=$api_key
WPH_EFAKT_API_BASE=$api_base
WPH_EFAKT_LIST_URL=$list_url
WPH_EFAKT_GET_XML_URL=$get_url

# Database Configuration
WPH_DB_HOST=$db_host
WPH_DB_PORT=$db_port
WPH_DB_NAME=$db_name
WPH_DB_USER=$db_user
$(if ($db_pass_plain) { "WPH_DB_PASS=$db_pass_plain" } else { "# WPH_DB_PASS=" })

# Security Options
WPH_WRITE_REMOTE=$write_remote_val
WPH_ALLOW_AUTO_CREATE=$auto_create_val

# Optional: Use FDW for remote access
WPH_USE_FDW=1

# Optional: Preserve existing MP prices
WPH_PRESERVE_EXISTING_MP=0
"@
    
    $env_content | Out-File -FilePath $env_path -Encoding UTF8
    Write-Host "✓ Konfigurimi u ruajt në: $env_path" -ForegroundColor Green
    
    # Security warning
    if ($db_pass_plain) {
        Write-Host "`n⚠️  SYGJERIM SIGURIE:" -ForegroundColor Yellow
        Write-Host "   .env file përmban fjalëkalimin në tekst të qartë." -ForegroundColor Gray
        Write-Host "   Sigurohu që ky file të mos shpërndahet." -ForegroundColor Gray
        Write-Host "   Shto në .gitignore: echo .env >> .gitignore" -ForegroundColor Gray
    }
}

# Test connection
Write-Host "`n🔍 Test i konfigurimit..." -ForegroundColor Cyan

$test_script = @"
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.efaktura_client import make_session
try:
    s = make_session()
    print('✓ API Session OK')
except Exception as e:
    print(f'❌ Gabim: {e}')
    sys.exit(1)
"@

$test_script | python -

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✓ Setup i plotë me sukses!" -ForegroundColor Green
    Write-Host "`n📚 PËRDORIMI:" -ForegroundColor Cyan
    Write-Host "   # Shkarko fakturat e muajit të kaluar" -ForegroundColor Gray
    Write-Host "   python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31" -ForegroundColor White
    Write-Host "`n   # Shkarko dhe importo automatikisht" -ForegroundColor Gray
    Write-Host "   python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import" -ForegroundColor White
    Write-Host "`n   # Dry-run për të parë çfarë do bëjë" -ForegroundColor Gray
    Write-Host "   python app/fetch_all_invoices.py --from 2025-10-01 --to 2025-10-31 --auto-import --dry-run" -ForegroundColor White
} else {
    Write-Host "`n⚠️  Setup u plotësua, por testi dështoi." -ForegroundColor Yellow
    Write-Host "   Kontrollo credentials dhe provo përsëri." -ForegroundColor Gray
}

Write-Host "`n" -NoNewline
Write-Host ("=" * 80) -ForegroundColor Cyan
