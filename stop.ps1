# Stops LinkeSearch: backend, frontend and the background Chrome of the app profile.
# Only processes whose command line points to this project folder are touched.
# Usage: powershell -ExecutionPolicy Bypass -File .\stop.ps1          (stop)
#        powershell -ExecutionPolicy Bypass -File .\stop.ps1 -List    (only show what would be stopped)
param([switch]$List)

$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$profileDir = Join-Path $root ".data\browser-profile"

function Find-AppProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $cmd = $_.CommandLine
        if (-not $cmd) { return $false }
        ($_.Name -eq "python.exe" -and $cmd -like "*-m app*" -and $cmd -like "*$backend*") -or
        ($_.Name -eq "node.exe" -and $cmd -like "*$frontend*") -or
        ($_.Name -eq "chrome.exe" -and $cmd -like "*$profileDir*" -and $cmd -notlike "*--type=*")
    }
}

$targets = @(Find-AppProcesses)
if ($targets.Count -eq 0) {
    Write-Host "LinkeSearch não está rodando." -ForegroundColor Yellow
    exit 0
}

foreach ($p in $targets) {
    $kind = switch ($p.Name) { "python.exe" { "Backend " } "node.exe" { "Frontend" } default { "Chrome  " } }
    if ($List) {
        Write-Host "$kind PID $($p.ProcessId)"
        continue
    }
    # /T also ends child processes (Chrome renderers, Next.js workers)
    & taskkill /PID $p.ProcessId /T /F 2>$null | Out-Null
    Write-Host "$kind encerrado (PID $($p.ProcessId))"
}

if (-not $List) {
    Start-Sleep -Milliseconds 500
    $left = @(Find-AppProcesses)
    if ($left.Count -eq 0) { Write-Host "LinkeSearch desligado." -ForegroundColor Green }
    else { Write-Host "Ainda restam $($left.Count) processo(s); rode o stop.ps1 de novo." -ForegroundColor Red }
}
