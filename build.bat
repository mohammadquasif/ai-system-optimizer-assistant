@echo off
:: ============================================================
:: AI System Optimizer Assistant - One-Click EXE Builder
:: Requires: Python 3.11+, PyInstaller
:: ============================================================

echo ==========================================
echo  AI System Optimizer - Build Script
echo ==========================================

:: Step 1: Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Dependency installation failed.
    pause & exit /b 1
)

:: Step 2: Build EXE with PyInstaller
echo [2/4] Building EXE with PyInstaller...
pyinstaller ^
    --name "AISystemOptimizer" ^
    --onedir ^
    --windowed ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    --add-data "config;config" ^
    --hidden-import PyQt6.QtSvg ^
    --hidden-import PyQt6.QtPrintSupport ^
    --hidden-import pyttsx3.drivers ^
    --hidden-import pyttsx3.drivers.sapi5 ^
    --hidden-import speech_recognition ^
    --hidden-import win32api ^
    --hidden-import win32con ^
    --hidden-import winreg ^
    --hidden-import winshell ^
    --collect-all PyQt6 ^
    --noconfirm ^
    app.py

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed.
    pause & exit /b 1
)

echo [3/4] Build complete! Output: dist\AISystemOptimizer\
echo [4/4] To create installer: run Inno Setup on installer\setup.iss

echo.
echo ==========================================
echo  BUILD SUCCESSFUL
echo  EXE: dist\AISystemOptimizer\AISystemOptimizer.exe
echo ==========================================
pause
