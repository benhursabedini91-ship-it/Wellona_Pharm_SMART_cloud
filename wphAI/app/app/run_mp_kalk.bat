@echo off
setlocal
set OB_OUTDIR=C:\Wellona\wphAI\out\orders
cd /d C:\Wellona\wphAI\app
"C:\Wellona\wphAI\app\.venv\Scripts\python.exe" mp_cli.py
endlocal
