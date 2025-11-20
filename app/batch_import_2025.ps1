# batch_import_2025.ps1
# Import i të gjitha fakturave të vitit 2025 në batch-e mujore
# Për të shmangur timeout dhe rate limiting

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "  BATCH IMPORT - Të gjitha fakturat 2025" -ForegroundColor Yellow
Write-Host "  Wellona Pharm SMART System" -ForegroundColor Gray
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""

# Configuration
$year = 2025
$current_month = (Get-Date).Month
$dry_run = $false  # Ndrysho në $true për test

# Parse arguments
if ($args -contains "--dry-run" -or $args -contains "-d") {
    $dry_run = $true
    Write-Host "⚠️  DRY-RUN MODE: Nuk do të shkruhet në bazë" -ForegroundColor Yellow
}

if ($args -contains "--help" -or $args -contains "-h") {
    Write-Host "PËRDORIMI:" -ForegroundColor Cyan
    Write-Host "  .\batch_import_2025.ps1           # Import real"
    Write-Host "  .\batch_import_2025.ps1 --dry-run # Test pa shkruar në DB"
    Write-Host ""
    exit 0
}

# Months to process (from January to current month)
$total_batches = $current_month
$completed = 0
$failed = 0
$total_invoices = 0
$total_imported = 0

Write-Host "📅 Do të importohen fakturat për $total_batches muaj ($year)" -ForegroundColor White
Write-Host ""

# Confirm before starting
if (-not $dry_run) {
    Write-Host "⚠️  KUJDES: Ky është import REAL në bazë!" -ForegroundColor Yellow
    $confirm = Read-Host "Dëshiron të vazhdosh? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host "✗ Anuluar nga përdoruesi" -ForegroundColor Red
        exit 0
    }
    Write-Host ""
}

# Process each month
for ($month = 1; $month -le $current_month; $month++) {
    $batch_num = $month
    
    # Calculate date range for this month
    $date_from = Get-Date -Year $year -Month $month -Day 1 -Format "yyyy-MM-dd"
    
    $last_day = [DateTime]::DaysInMonth($year, $month)
    $date_to = Get-Date -Year $year -Month $month -Day $last_day -Format "yyyy-MM-dd"
    
    # If current month, use today as end date
    if ($month -eq $current_month) {
        $date_to = Get-Date -Format "yyyy-MM-dd"
    }
    
    $month_name = (Get-Date -Year $year -Month $month -Day 1).ToString("MMMM", [System.Globalization.CultureInfo]::CreateSpecificCulture("sq-AL"))
    
    Write-Host "┌$("─" * 78)┐" -ForegroundColor Cyan
    Write-Host "│ BATCH $batch_num/$total_batches`: $month_name $year ($date_from deri $date_to)" -ForegroundColor Cyan -NoNewline
    Write-Host (" " * (78 - 16 - $month_name.Length - 4 - $date_from.Length - 6 - $date_to.Length)) -NoNewline
    Write-Host "│" -ForegroundColor Cyan
    Write-Host "└$("─" * 78)┘" -ForegroundColor Cyan
    
    # Build command
    $cmd_args = @(
        "app/fetch_all_invoices.py",
        "--from", $date_from,
        "--to", $date_to,
        "--auto-import",
        "--delay", "0.5"
    )
    
    if ($dry_run) {
        $cmd_args += "--dry-run"
    }
    
    # Execute
    $start_time = Get-Date
    
    try {
        python $cmd_args
        $exit_code = $LASTEXITCODE
        
        $end_time = Get-Date
        $duration = ($end_time - $start_time).TotalSeconds
        
        if ($exit_code -eq 0) {
            $completed++
            Write-Host "✓ Batch $batch_num u përfundua me sukses (kohëzgjatja: $([math]::Round($duration, 1))s)" -ForegroundColor Green
        } else {
            $failed++
            Write-Host "✗ Batch $batch_num dështoi (exit code: $exit_code)" -ForegroundColor Red
        }
        
    } catch {
        $failed++
        Write-Host "✗ Batch $batch_num dështoi: $_" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Short delay between batches
    if ($month -lt $current_month) {
        Write-Host "⏸  Pushim 5 sekonda para batch-it të radhës..." -ForegroundColor Gray
        Start-Sleep -Seconds 5
        Write-Host ""
    }
}

# Final summary
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host "  PËRMBLEDHJE FINALE" -ForegroundColor Yellow
Write-Host ("=" * 80) -ForegroundColor Cyan
Write-Host ""
Write-Host "Batch-e totale:      $total_batches" -ForegroundColor White
Write-Host "✓ Të suksesshme:    $completed" -ForegroundColor Green
Write-Host "✗ Të dështuara:     $failed" -ForegroundColor Red
Write-Host ""

if ($dry_run) {
    Write-Host "⚠️  DRY-RUN: Nuk u shkrua asgjë në bazë" -ForegroundColor Yellow
}

if ($failed -eq 0) {
    Write-Host "🎉 TË GJITHA BATCH-ET U PËRFUNDUAN ME SUKSES!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Disa batch-e dështuan. Kontrollo logs për detaje." -ForegroundColor Yellow
}

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor Cyan

# Exit with appropriate code
if ($failed -gt 0) {
    exit 1
} else {
    exit 0
}
