@echo off
rem Double-click to stop LinkeSearch (backend, frontend and background Chrome)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
timeout /t 4 >nul
