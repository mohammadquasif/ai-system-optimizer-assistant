@echo off
setlocal EnableDelayedExpansion
title AI System Optimizer - Uninstall
color 0C

set "SCRIPT_DIR=%~dp0"

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
    goto :launch
)
py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py"
    goto :launch
)

echo  [ERROR] Python not found. Cannot launch uninstaller.
pause
exit /b 1

:launch
if exist "%SCRIPT_DIR%installer_gui.py" (
    %PYTHON_CMD% "%SCRIPT_DIR%installer_gui.py"
    exit /b 0
)
echo  [ERROR] installer_gui.py not found.
pause
exit /b 1
