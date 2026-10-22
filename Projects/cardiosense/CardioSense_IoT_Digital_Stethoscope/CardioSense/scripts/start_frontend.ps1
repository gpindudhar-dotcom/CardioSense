$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) { npm install }
Write-Host "Starting CardioSense frontend..."
npm run dev
