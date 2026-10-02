Set-Location -Path $PSScriptRoot

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  Starting jBahr's Clip Generator...                " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    Write-Host "[INFO] Launching with Virtual Environment Python..." -ForegroundColor Green
    & $venvPython "app.py"
} else {
    Write-Host "[INFO] Launching with System Python..." -ForegroundColor Yellow
    python "app.py"
}

if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Application exited with error code $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
