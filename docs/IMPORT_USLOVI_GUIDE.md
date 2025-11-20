# Import Supplier Excel Files - Quick Start Guide

## Prerequisites

1. **Install Python dependencies:**
   ```powershell
   pip install pandas openpyxl psycopg2
   ```

2. **Set database environment variables:**
   ```powershell
   $env:WPH_DB_HOST = "localhost"
   $env:WPH_DB_PORT = "5432"
   $env:WPH_DB_NAME = "wph_ai"
   $env:WPH_DB_USER = "postgres"
   $env:WPH_DB_PASS = "your_password"
   ```

3. **Place Excel files in `EB/UsloviDobavljaca/`:**
   - Phoenix.xlsx
   - Sopharma.xlsx
   - Vega.xlsx
   - Farmalogist.xlsx

## Usage

### Import all suppliers
```powershell
python bin/import_uslovi_excel.py
```

### Import specific supplier
```powershell
python bin/import_uslovi_excel.py --supplier PHOENIX
```

### Specify custom data directory
```powershell
python bin/import_uslovi_excel.py --data-dir "C:\CustomPath\Suppliers"
```

## Verification

After import, verify the update in PostgreSQL:

```sql
-- Check rabat percentages by supplier
SELECT supplier_code, 
       COUNT(*) as products,
       AVG(rabat_pct) as avg_rabat,
       MIN(rabat_pct) as min_rabat,
       MAX(rabat_pct) as max_rabat
  FROM stg.pricefeed
 WHERE rabat_pct IS NOT NULL
 GROUP BY supplier_code
 ORDER BY supplier_code;

-- Test supplier selection with rabat
SELECT * FROM wph_core.get_orders(
    target_days := 30,
    sales_window := 60,
    include_zero := false,
    search_query := 'DEXOMEN'
);
```

## Troubleshooting

### Missing Excel files
If you see "Excel file missing" warnings, ensure files are in `EB/UsloviDobavljaca/` with correct names.

### Column index errors
If you see "Column index out of range", check the Excel file structure matches the mapping in `configs/uslovi-mapping.json`.

### Database connection failed
Verify environment variables are set correctly:
```powershell
echo $env:WPH_DB_HOST
echo $env:WPH_DB_NAME
```

### No rows updated
This means no matching barcodes were found in `stg.pricefeed`. Check:
1. Barcode format matches (15-digit max, digits only)
2. Supplier code matches (PHOENIX, VEGA, SOPHARMA, FARMALOGIST)
3. Pricefeed table has existing records for that supplier

## Automation

Add to nightly ETL pipeline:

```powershell
# Run daily at 02:00 AM
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$action = New-ScheduledTaskAction -Execute "python" -Argument "bin/import_uslovi_excel.py"
Register-ScheduledTask -TaskName "WPH_ImportUslovi" -Trigger $trigger -Action $action
```

## Log Files

Import logs: `logs/import_uslovi.log`

Check for errors:
```powershell
Get-Content logs/import_uslovi.log | Select-String "ERROR"
```
