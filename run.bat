@echo off
setlocal EnableDelayedExpansion

title AI System Optimizer
color 0B

set "SCRIPT_DIR=%~dp0"

:: Find pythonw (silent launch, no console window)
set "PYTHONW_PATH="
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do set "PYTHONW_PATH=%%i"
if "!PYTHONW_PATH!"=="" set "PYTHONW_PATH=python"

:: Check python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python not found. Please run INSTALL.bat first.
    pause
    exit /b 1
)

echo  Launching AI System Optimizer...
start "" "!PYTHONW_PATH!" "%SCRIPT_DIR%app.py"
timeout /t 2 /nobreak >nul
exit /b 0
