# CardioSense Windows one-command software start
# ESP32 firmware must be flashed separately before hardware streaming works.
# Educational prototype — not a medical device.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== CardioSense startup (Windows 11) ===" -ForegroundColor Cyan
Write-Host "Educational prototype — not a medical diagnostic device." -ForegroundColor Yellow

function Assert-Command($name, $check) {
  Write-Host "Checking $name..." -NoNewline
  try {
    $ver = & $check
    Write-Host " OK ($ver)" -ForegroundColor Green
  } catch {
    Write-Host " MISSING" -ForegroundColor Red
    throw "$name is required. See docs/installation_windows.md"
  }
}

Assert-Command "Python" { python --version }
Assert-Command "Node.js" { node --version }
Assert-Command "npm" { npm --version }

Write-Host "Checking PlatformIO (optional for firmware)..." -NoNewline
try {
  $pio = python -m platformio --version
  Write-Host " OK ($pio)" -ForegroundColor Green
} catch {
  Write-Host " not found (firmware flash will need PlatformIO)" -ForegroundColor Yellow
}

$venv = Join-Path $Root ".venv"
if (-not (Test-Path $venv)) {
  Write-Host "Creating Python virtual environment..."
  python -m venv $venv
}

$py = Join-Path $venv "Scripts\python.exe"
$pip = Join-Path $venv "Scripts\pip.exe"

Write-Host "Installing backend dependencies..."
& $pip install --upgrade pip
& $pip install -r (Join-Path $Root "backend\requirements.txt")

Write-Host "Installing frontend dependencies..."
Push-Location (Join-Path $Root "frontend")
npm install
Pop-Location

# Copy env examples if needed
if (-not (Test-Path (Join-Path $Root ".env"))) {
  Copy-Item (Join-Path $Root ".env.example") (Join-Path $Root ".env")
}
if (-not (Test-Path (Join-Path $Root "backend\.env"))) {
  Copy-Item (Join-Path $Root "backend\.env.example") (Join-Path $Root "backend\.env")
}

Write-Host "Starting backend on http://127.0.0.1:8000 ..."
$backend = Start-Process -PassThru -FilePath $py -ArgumentList @(
  "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--reload"
) -WorkingDirectory $Root -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Starting frontend on http://127.0.0.1:5173 ..."
$frontend = Start-Process -PassThru -FilePath "npm" -ArgumentList @("run", "dev") -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Normal

Write-Host ""
Write-Host "CardioSense software is starting:" -ForegroundColor Green
Write-Host "  Dashboard : http://127.0.0.1:5173"
Write-Host "  API docs  : http://127.0.0.1:8000/docs"
Write-Host "  Health    : http://127.0.0.1:8000/health"
Write-Host ""
Write-Host "Flash ESP32 firmware separately (see firmware/esp32/README.md), then stream to the backend."
Write-Host "Press Enter to stop both processes..."
[void][System.Console]::ReadLine()

if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
Write-Host "Stopped."
