$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$venv = Join-Path $Root ".venv"
if (-not (Test-Path $venv)) { python -m venv $venv }
$py = Join-Path $venv "Scripts\python.exe"
& (Join-Path $venv "Scripts\pip.exe") install -r (Join-Path $Root "backend\requirements.txt")
Write-Host "Starting CardioSense backend..."
& $py -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
