$here = Split-Path -Parent $(\System.Management.Automation.InvocationInfo.MyCommand.Path)
Set-Location ""
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\pip.exe install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
$env:OB_OUTDIR = 'C:\Wellona\wphAI\out\orders'
# CWD -> work që order_brain të gjejë inputet
Push-Location .\work
.\.venv\Scripts\python.exe ..\runner_cli.py
Pop-Location
