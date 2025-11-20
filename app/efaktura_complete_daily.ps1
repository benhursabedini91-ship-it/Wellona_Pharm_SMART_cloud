# eFaktura Complete Daily Automation
# Combines: Subscription + Fetch + Import + Report

$ErrorActionPreference = "Stop"

# Configuration
$env:WPH_EFAKT_API_KEY = "f7b40af0-9689-4872-8d59-4779f7961175"
$env:WPH_DB_PASS = "wellona-server"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$LogFile = "logs\efaktura_daily_$(Get-Date -Format 'yyyy-MM-dd').log"

function Write-Log {
    param($Message, $Color = "White")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] $Message"
    Write-Host $LogMessage -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $LogMessage
}

# Create logs directory
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

Write-Log "========================================" "Cyan"
Write-Log "  eFaktura Daily Automation" "Cyan"
Write-Log "========================================" "Cyan"

# STEP 1: Subscribe for notifications
Write-Log "`n[1/5] Subscribing for email notifications..." "Yellow"
try {
    $result = python efaktura_webhook.py subscribe 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "✅ Subscription successful" "Green"
        Write-Log "$result" "Gray"
    } else {
        Write-Log "⚠️  Subscription warning: $result" "Yellow"
    }
} catch {
    Write-Log "❌ Subscription failed: $_" "Red"
}

# STEP 2: Fetch new invoices (last 7 days to be safe)
Write-Log "`n[2/5] Fetching new invoices..." "Yellow"
try {
    $dateFrom = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
    $dateTo = (Get-Date).ToString("yyyy-MM-dd")
    
    Write-Log "Date range: $dateFrom to $dateTo" "Gray"
    
    $result = python fetch_all_invoices.py --from $dateFrom --to $dateTo 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "✅ Fetch successful" "Green"
        # Count XMLs
        $xmlCount = (Get-ChildItem -Path "..\staging\faktura_uploads" -Filter "*.xml" -ErrorAction SilentlyContinue).Count
        Write-Log "Total XML files: $xmlCount" "Gray"
    } else {
        Write-Log "❌ Fetch failed: $result" "Red"
    }
} catch {
    Write-Log "❌ Fetch exception: $_" "Red"
}

# STEP 3: Dry-run import (safety check)
Write-Log "`n[3/5] Running import dry-run..." "Yellow"
try {
    $result = python import_efaktura_safe.py --dry-run --user smart_pedja 2>&1
    
    if ($result -match "(\d+) files parsed successfully") {
        $parsedCount = $matches[1]
        Write-Log "✅ Dry-run OK: $parsedCount files parsed" "Green"
        
        # Check for duplicates
        if ($result -match "(\d+) duplicates found") {
            $dupCount = $matches[1]
            Write-Log "⚠️  $dupCount duplicates detected (will skip)" "Yellow"
        } else {
            Write-Log "No duplicates found" "Gray"
        }
        
        # STEP 4: Real import (if dry-run passed)
        Write-Log "`n[4/5] Importing to database..." "Yellow"
        
        # Uncomment to enable real import:
        # $importResult = python import_efaktura_safe.py --user smart_pedja 2>&1
        # if ($LASTEXITCODE -eq 0) {
        #     Write-Log "✅ Import successful" "Green"
        # } else {
        #     Write-Log "❌ Import failed: $importResult" "Red"
        # }
        
        Write-Log "⚠️  Real import DISABLED (uncomment to enable)" "Yellow"
        
    } else {
        Write-Log "⚠️  Dry-run unclear result: $result" "Yellow"
    }
} catch {
    Write-Log "❌ Import exception: $_" "Red"
}

# STEP 5: Generate summary report
Write-Log "`n[5/5] Generating summary report..." "Yellow"
try {
    $xmlFiles = Get-ChildItem -Path "..\staging\faktura_uploads" -Filter "INV_*.xml" -ErrorAction SilentlyContinue
    $xmlCount = $xmlFiles.Count
    
    Write-Log "Summary:" "Cyan"
    Write-Log "  - Total XML files: $xmlCount" "Gray"
    
    if ($xmlCount -gt 0) {
        # Get latest file
        $latest = $xmlFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        Write-Log "  - Latest file: $($latest.Name)" "Gray"
        Write-Log "  - Last modified: $($latest.LastWriteTime)" "Gray"
        
        # Extract suppliers (basic parsing)
        $suppliers = @{}
        foreach ($xml in $xmlFiles | Select-Object -First 50) {
            $content = Get-Content $xml.FullName -Raw -Encoding UTF8
            if ($content -match '<cac:PartyName>\s*<cbc:Name>([^<]+)</cbc:Name>') {
                $supplier = $matches[1]
                if ($suppliers.ContainsKey($supplier)) {
                    $suppliers[$supplier]++
                } else {
                    $suppliers[$supplier] = 1
                }
            }
        }
        
        Write-Log "  - Suppliers:" "Gray"
        foreach ($supplier in $suppliers.Keys | Sort-Object { $suppliers[$_] } -Descending) {
            Write-Log "    * $supplier : $($suppliers[$supplier]) invoices" "Gray"
        }
    }
    
    Write-Log "✅ Summary complete" "Green"
    
} catch {
    Write-Log "⚠️  Summary generation failed: $_" "Yellow"
}

# Final status
Write-Log "`n========================================" "Cyan"
Write-Log "  Daily Automation Complete" "Cyan"
Write-Log "  Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" "Cyan"
Write-Log "  Log: $LogFile" "Cyan"
Write-Log "========================================" "Cyan"

# Check subscription status
if (Test-Path "efaktura_subscription_id.txt") {
    $subContent = Get-Content "efaktura_subscription_id.txt" -Raw
    if ($subContent -match "Valid until: (\d{4}-\d{2}-\d{2})") {
        $validUntil = $matches[1]
        Write-Log "`n🔔 Subscription active until: $validUntil" "Green"
    }
}

Write-Log "`n✅ All tasks completed!" "Green"
