@echo off
setlocal
cd /d "%~dp0"

if exist "Auditer.exe" (
    start "" "Auditer.exe" %*
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
