# Starts LinkeSearch locally: backend (127.0.0.1:8000) and frontend (localhost:3000).
# Usage: powershell -ExecutionPolicy Bypass -File .\start.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$python = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Ambiente Python não encontrado. Veja a seção Instalação do README." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Host "Dependências do frontend não instaladas. Rode: cd frontend; npm install" -ForegroundColor Red
    exit 1
}

$env:PYTHONIOENCODING = "utf-8"
$backend = Start-Process -FilePath $python -ArgumentList "-m", "app" -WorkingDirectory (Join-Path $root "backend") -PassThru -NoNewWindow
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory (Join-Path $root "frontend") -PassThru -NoNewWindow

Write-Host "Backend:  http://127.0.0.1:8000  (PID $($backend.Id))"
Write-Host "Frontend: http://localhost:3000  (PID $($frontend.Id))"
Start-Sleep -Seconds 6
Start-Process "http://localhost:3000"
Write-Host "Pressione Ctrl+C para encerrar."
try {
    Wait-Process -Id $backend.Id
} finally {
    foreach ($p in @($backend, $frontend)) {
        if (-not $p.HasExited) { & taskkill /PID $p.Id /T /F | Out-Null }
    }
}
