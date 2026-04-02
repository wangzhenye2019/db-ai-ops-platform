$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "Backend: compileall"
python -m compileall backend

Write-Host "Backend: pytest"
$env:PYTHONPATH = "backend"
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
pytest -q backend/tests

Write-Host "Frontend: build"
Set-Location (Join-Path $PSScriptRoot "..\frontend")
npm ci
npm run build
