@echo off
set PYTHON_EXE=C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
if not exist "%PYTHON_EXE%" (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_EXE=python
    ) else (
        echo Python executable not found.
        pause
        exit /b 1
    )
)

"%PYTHON_EXE%" main.py %*
