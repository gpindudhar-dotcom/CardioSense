# CardioSense validation script (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$failures = @()

Write-Host "=== CardioSense test_project.ps1 ===" -ForegroundColor Cyan

$venv = Join-Path $Root ".venv"
if (-not (Test-Path $venv)) { python -m venv $venv }
$py = Join-Path $venv "Scripts\python.exe"
& (Join-Path $venv "Scripts\pip.exe") install -r (Join-Path $Root "backend\requirements.txt") | Out-Null
& (Join-Path $venv "Scripts\pip.exe") install pytest pytest-asyncio httpx | Out-Null

Write-Host "[1/4] Backend unit tests..."
& $py -m pytest tests backend/tests -q
if ($LASTEXITCODE -ne 0) { $failures += "backend-tests" }

Write-Host "[2/4] Frontend install + build..."
Push-Location (Join-Path $Root "frontend")
npm install
if ($LASTEXITCODE -ne 0) { $failures += "npm-install" }
npm run build
if ($LASTEXITCODE -ne 0) { $failures += "frontend-build" }
Pop-Location

Write-Host "[3/4] Firmware PlatformIO build..."
try {
  Push-Location (Join-Path $Root "firmware\esp32")
  & $py -m platformio run
  if ($LASTEXITCODE -ne 0) { $failures += "firmware-build" }
  Pop-Location
} catch {
  Write-Host "PlatformIO build failed: $_" -ForegroundColor Red
  $failures += "firmware-build"
  Pop-Location -ErrorAction SilentlyContinue
}

Write-Host "[4/4] Health import check..."
& $py -c "from app.main import app; print('app-ok', app.title)" 
if ($LASTEXITCODE -ne 0) { $failures += "import-check" }

if ($failures.Count -eq 0) {
  Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
  exit 0
} else {
  Write-Host ("FAILURES: " + ($failures -join ", ")) -ForegroundColor Red
  exit 1
}
