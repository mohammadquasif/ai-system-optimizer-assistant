@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: AI System Optimizer Assistant - Full Auto-Setup
:: Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
:: GitHub: https://github.com/mohammadquasif/ai-system-optimizer
:: License: Personal Use Only (Non-Commercial)
::
:: This script auto-installs everything needed:
::   1. Checks Windows 10/11
::   2. Checks Python - downloads and installs if missing
::   3. Installs all Python packages
::   4. Checks Ollama - downloads and installs if missing
::   5. Checks AI model - skips download if already installed
::   6. Creates desktop shortcut + Windows startup entry
::   7. Launches the app
:: ============================================================

title AI System Optimizer - Setup
color 0B
cls

echo.
echo  =======================================================
echo    AI System Optimizer Assistant v1.0.0
echo    by Mohammad Quasif (DBA AI, B.Tech CS)
echo    github.com/mohammadquasif/ai-system-optimizer
echo  =======================================================
echo.
echo  Starting automatic setup...
echo.

set "SCRIPT_DIR=%~dp0"
set "TEMP_DIR=%TEMP%\AIOptimizerSetup"
set "PYTHON_URL=https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe"
set "PYTHON_INSTALLER=%TEMP_DIR%\python313.exe"
set "OLLAMA_URL=https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
set "OLLAMA_INSTALLER=%TEMP_DIR%\OllamaSetup.exe"
set "OFFLINE_OLLAMA=%SCRIPT_DIR%installer\ollama\OllamaSetup.exe"
set "SHORTCUT=%USERPROFILE%\Desktop\AI System Optimizer.lnk"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: ============================================================
:: STEP 1 - PYTHON CHECK
:: ============================================================
echo [1/7] Checking Python...
echo.

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    echo  [OK] Python !PYVER! is already installed.
    set "PYTHON_CMD=python"
    goto :step2
)

py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Python found via py launcher.
    set "PYTHON_CMD=py"
    goto :step2
)

echo  [!] Python NOT found. Downloading Python 3.13 automatically...
echo      Download size: ~25 MB. Please wait.
echo.

ping -n 1 8.8.8.8 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] No internet connection detected.
    echo.
    echo  Please install Python manually:
    echo  1. Open https://www.python.org/downloads/
    echo  2. Download Python 3.13 for Windows
    echo  3. Run the installer and check "Add Python to PATH"
    echo  4. Run INSTALL.bat again
    echo.
    pause
    exit /b 1
)

echo  Downloading Python 3.13 from python.org...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing"

if not exist "%PYTHON_INSTALLER%" (
    echo  [ERROR] Python download failed.
    echo  Please download manually from https://python.org
    pause
    exit /b 1
)

echo  Installing Python 3.13 (this takes about 1-2 minutes)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1

:: Reload PATH so python command is found in this session
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "UPATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SPATH=%%b"
set "PATH=!SPATH!;!UPATH!"

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [INFO] Python installed but PATH needs a system restart.
    echo  Please restart your PC and run INSTALL.bat again.
    pause
    exit /b 0
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  [OK] Python !PYVER! installed successfully.
set "PYTHON_CMD=python"

:step2
echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 2 - PYTHON PACKAGES
:: ============================================================
echo [2/7] Installing Python packages...
echo       (First run: 3-5 minutes. Next time: instant)
echo.

%PYTHON_CMD% -m pip install --upgrade pip --quiet --disable-pip-version-check >nul 2>&1

if exist "%SCRIPT_DIR%requirements.txt" (
    %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet --no-warn-script-location
    if !ERRORLEVEL! NEQ 0 (
        echo  Some packages failed. Installing core packages individually...
        %PYTHON_CMD% -m pip install PyQt6 psutil pyttsx3 requests cryptography pywin32 winshell openai anthropic --quiet
    )
) else (
    echo  requirements.txt not found. Installing core packages...
    %PYTHON_CMD% -m pip install PyQt6 psutil pyttsx3 requests cryptography pywin32 winshell openai anthropic --quiet
)

echo  [OK] Python packages installed.
echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 3 - OLLAMA CHECK
:: ============================================================
echo [3/7] Checking Ollama AI engine...
echo.

ollama --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Ollama is already installed.
    goto :start_ollama_service
)

echo  [!] Ollama not found.

:: Check offline installer first
if exist "%OFFLINE_OLLAMA%" (
    echo  Found offline installer. Installing Ollama...
    "%OFFLINE_OLLAMA%" /S
    timeout /t 5 /nobreak >nul
    echo  [OK] Ollama installed from offline package.
    goto :start_ollama_service
)

:: Check internet and download
ping -n 1 8.8.8.8 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [WARN] No internet. Ollama cannot be installed.
    echo         App will run without AI assistant.
    echo         To enable AI offline: place OllamaSetup.exe in installer\ollama\
    goto :step4
)

echo  Downloading Ollama (~100 MB). Please wait...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%OLLAMA_URL%' -OutFile '%OLLAMA_INSTALLER%' -UseBasicParsing"

if exist "%OLLAMA_INSTALLER%" (
    echo  Installing Ollama silently...
    "%OLLAMA_INSTALLER%" /S
    timeout /t 6 /nobreak >nul
    if not exist "%SCRIPT_DIR%installer\ollama\" mkdir "%SCRIPT_DIR%installer\ollama\"
    copy "%OLLAMA_INSTALLER%" "%OFFLINE_OLLAMA%" >nul 2>&1
    echo  [OK] Ollama installed.
) else (
    echo  [WARN] Ollama download failed. App will run without AI.
)
goto :step4

:start_ollama_service
echo  Checking if Ollama service is running...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Starting Ollama service in background...
    start "" /B ollama serve
    timeout /t 4 /nobreak >nul
    echo  [OK] Ollama service started.
) else (
    echo  [OK] Ollama service is already running.
)

:step4
echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 4 - AI MODEL CHECK (skip if already installed)
:: ============================================================
echo [4/7] Checking AI model...
echo.

set "MODEL_FOUND=0"
set "FOUND_MODEL=none"

ollama --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [SKIP] Ollama not available. Skipping model check.
    goto :step5
)

:: Check each preferred model (smallest first)
ollama list 2>nul | findstr /i "qwen2.5:0.5b" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "MODEL_FOUND=1"
    set "FOUND_MODEL=qwen2.5:0.5b"
    goto :model_result
)

ollama list 2>nul | findstr /i "qwen2.5:1b" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "MODEL_FOUND=1"
    set "FOUND_MODEL=qwen2.5:1b"
    goto :model_result
)

ollama list 2>nul | findstr /i "llama3.2:1b" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "MODEL_FOUND=1"
    set "FOUND_MODEL=llama3.2:1b"
    goto :model_result
)

ollama list 2>nul | findstr /i "qwen2.5:1.5b" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "MODEL_FOUND=1"
    set "FOUND_MODEL=qwen2.5:1.5b"
    goto :model_result
)

:: Also accept any qwen or llama model
ollama list 2>nul | findstr /i "qwen llama phi gemma tinyllama" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "MODEL_FOUND=1"
    set "FOUND_MODEL=existing model"
    goto :model_result
)

:model_result
if "!MODEL_FOUND!"=="1" (
    echo  [OK] Found model: !FOUND_MODEL!
    echo       Skipping download - will use existing model.
) else (
    echo  [INFO] No AI model installed yet.
    echo         App will download qwen2.5:0.5b on first launch.
    echo         Size: ~400 MB. Internet required.
)

:step5
echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 5 - DESKTOP SHORTCUT
:: ============================================================
echo [5/7] Creating desktop shortcut...
echo.

powershell -NoProfile -Command "& { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = 'pythonw'; $s.Arguments = '\"%SCRIPT_DIR%app.py\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'AI System Optimizer by Mohammad Quasif'; $s.Save() }" 2>nul

if exist "%SHORTCUT%" (
    echo  [OK] Desktop shortcut created.
) else (
    echo  [WARN] Could not create shortcut. Run app.py manually.
)

echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 6 - WINDOWS STARTUP ENTRY
:: ============================================================
echo [6/7] Adding to Windows startup...
echo.

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "AISystemOptimizer" /t REG_SZ /d "pythonw \"%SCRIPT_DIR%app.py\"" /f >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo  [OK] App will now launch automatically on Windows startup.
    echo       It will greet you and then close when idle to free RAM.
) else (
    echo  [WARN] Startup entry skipped.
)

echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 7 - LAUNCH
:: ============================================================
echo [7/7] Launching AI System Optimizer...
echo.

echo  =========================================================
echo    Setup Complete!
echo.
echo    What happens next:
echo    - A splash screen will appear
echo    - The app checks if AI setup is needed
echo    - You will hear a voice greeting
echo    - App auto-closes after 5 min idle (frees RAM)
echo    - Double-click desktop icon to relaunch anytime
echo  =========================================================
echo.

start "" pythonw "%SCRIPT_DIR%app.py"

echo  App launched successfully!
echo.
echo  Press any key to close this window...
pause >nul
exit /b 0
