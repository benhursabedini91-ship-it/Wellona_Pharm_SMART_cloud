@echo off
setlocal
set OB_OUTDIR=C:\Wellona\wphAI\out\orders
cd /d C:\Wellona\wphAI\app
"C:\Wellona\wphAI\app\.venv\Scripts\python.exe" run_once.py
rem open latest export
for /f "usebackq delims=" %%F in (powershell -NoProfile -Command ^
  "Get-ChildItem -Path 'C:\Wellona\wphAI\out\orders' -Filter *.xlsx -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -Expand FullName") do set LAST=%%F
if not "%LAST%"=="" start "" explorer.exe /select,"%LAST%"
endlocal
