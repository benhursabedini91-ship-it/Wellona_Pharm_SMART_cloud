param(
  [string]$OutDir = "C:\Wellona\wphAI\snapshots"
)
$ErrorActionPreference = 'Stop'
$ts = Get-Date -Format 'yyyyMMdd_HHmm'
$dir = Join-Path $OutDir "baseline_$ts"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# 1) Save baseline patch copy used
Copy-Item "C:\Wellona\wphAI\patches\baseline_erp_identik_2025-11-01.sql" -Destination (Join-Path $dir "baseline_patch.sql") -Force

# 2) DB schema-only dump (fast, reproducible)
$pgdump = (Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter pg_dump.exe | Select-Object -First 1).FullName
$env:PGPASSWORD = "0262000"
& $pgdump -h 127.0.0.1 -p 5432 -U postgres -d wph_ai -F p -s -f (Join-Path $dir "wph_ai_schema.sql") | Out-Null

# 3) Optional full backup (commented; enable if needed)
# & $pgdump -h 127.0.0.1 -p 5432 -U postgres -d wph_ai -F c -f (Join-Path $dir "wph_ai_full.dump") | Out-Null
