# Aktivizo venv
$here = Split-Path -Parent $(\System.Management.Automation.InvocationInfo.MyCommand.Path)
Set-Location ""
if (!(Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\pip.exe install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

# Vendos OB_OUTDIR në sesion
$env:OB_OUTDIR = 'C:\Wellona\wphAI\out\orders'

# Nis Waitress (Flask app në portin 5001)
.\.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:5001 app:app
