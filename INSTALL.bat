@echo off
setlocal EnableDelayedExpansion

title AI System Optimizer - Setup v1.1
color 0B
cls

echo.
echo  ============================================================
echo    AI System Optimizer Assistant v1.0.0
echo    by Mohammad Quasif  ^|  DBA AI ^| B.Tech CS
echo    github.com/mohammadquasif/ai-system-optimizer-assistant
echo  ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "TEMP_DIR=%TEMP%\AIOptimizerSetup"
set "PYTHON_URL=https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe"
set "PYTHON_INSTALLER=%TEMP_DIR%\python313.exe"
set "OLLAMA_URL=https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
set "OLLAMA_INSTALLER=%TEMP_DIR%\OllamaSetup.exe"
set "OFFLINE_OLLAMA=%SCRIPT_DIR%installer\ollama\OllamaSetup.exe"
set "SHORTCUT=%USERPROFILE%\Desktop\AI System Optimizer.lnk"
set "TARGET_MODEL=qwen2.5:0.5b"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: ============================================================
:: STEP 1 - PYTHON CHECK
:: ============================================================
echo [1/6] Checking Python...

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    echo  [OK] Python !PYVER! found.
    set "PYTHON_CMD=python"
    goto :step2
)

py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Python found via py launcher.
    set "PYTHON_CMD=py"
    goto :step2
)

echo  [!] Python NOT found. Downloading Python 3.13...
ping -n 1 8.8.8.8 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] No internet. Install Python from https://www.python.org then run INSTALL.bat again.
    pause
    exit /b 1
)

powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing" >nul 2>&1
if not exist "%PYTHON_INSTALLER%" (
    echo  [ERROR] Python download failed. Download manually from https://python.org
    pause
    exit /b 1
)

echo  Installing Python 3.13...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1
timeout /t 5 /nobreak >nul

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [INFO] Restart your PC then run INSTALL.bat again.
    pause
    exit /b 0
)
set "PYTHON_CMD=python"

:step2
echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 2 - CHECK AND FIX STALE AI SETTINGS
:: ============================================================
echo [2/6] Checking AI settings...

if exist "%SCRIPT_DIR%_setup_helper.py" (
    %PYTHON_CMD% "%SCRIPT_DIR%_setup_helper.py" check
) else (
    echo  [INFO] Setup helper not found, skipping settings check.
)

echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 3 - PYTHON PACKAGES
:: ============================================================
echo [3/6] Installing Python packages...
echo       (First time: 3-5 minutes. Subsequent runs: instant)

%PYTHON_CMD% -m pip install --upgrade pip --quiet --disable-pip-version-check >nul 2>&1

if exist "%SCRIPT_DIR%requirements.txt" (
    echo  Installing from requirements.txt...
    %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet --no-warn-script-location
    if !ERRORLEVEL! NEQ 0 (
        echo  Retrying with individual packages...
        %PYTHON_CMD% -m pip install PyQt6 psutil pyttsx3 requests cryptography pywin32 winshell openai anthropic --quiet
    )
) else (
    %PYTHON_CMD% -m pip install PyQt6 psutil pyttsx3 requests cryptography pywin32 winshell openai anthropic --quiet
)
echo  [OK] Packages installed.

echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 4 - OLLAMA CHECK AND START
:: ============================================================
echo [4/6] Checking Ollama AI engine...

ollama --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Ollama already installed.
    goto :start_service
)

echo  [!] Ollama not found.

if exist "%OFFLINE_OLLAMA%" (
    echo  Installing from offline package...
    "%OFFLINE_OLLAMA%" /S
    timeout /t 8 /nobreak >nul
    echo  [OK] Ollama installed from offline package.
    goto :start_service
)

ping -n 1 8.8.8.8 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [WARN] No internet - Ollama skipped. App will run without AI.
    goto :step5
)

echo  Downloading Ollama (~100 MB)...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '%OLLAMA_URL%' -OutFile '%OLLAMA_INSTALLER%' -UseBasicParsing" >nul 2>&1

if exist "%OLLAMA_INSTALLER%" (
    echo  Installing Ollama...
    "%OLLAMA_INSTALLER%" /S
    timeout /t 8 /nobreak >nul
    if not exist "%SCRIPT_DIR%installer\ollama\" mkdir "%SCRIPT_DIR%installer\ollama\"
    copy "%OLLAMA_INSTALLER%" "%OFFLINE_OLLAMA%" >nul 2>&1
    echo  [OK] Ollama installed.
) else (
    echo  [WARN] Ollama download failed. App will run without AI.
    goto :step5
)

:start_service
echo  Checking Ollama service...
curl -s --max-time 3 http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Starting Ollama service...
    start "" /B ollama serve
    timeout /t 6 /nobreak >nul
)
curl -s --max-time 3 http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Ollama service running.
) else (
    echo  [WARN] Ollama service not responding. Will retry on app launch.
    goto :step5
)

:: Check if 0.5b model is installed
ollama list 2>nul | findstr /i "qwen2.5:0.5" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] qwen2.5:0.5b already installed.
    goto :step5
)

:: Pull the model
echo.
echo  Downloading AI model qwen2.5:0.5b (~400 MB)...
echo  Note: One-time download. Please wait.
ollama pull qwen2.5:0.5b
if %ERRORLEVEL% EQU 0 (
    echo  [OK] qwen2.5:0.5b ready.
) else (
    echo  [WARN] Model download failed. App will retry on launch.
)

:step5
echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 5 - DESKTOP SHORTCUT + STARTUP ENTRY
:: ============================================================
echo [5/6] Creating shortcuts...

:: Find pythonw
set "PYTHONW_PATH="
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do set "PYTHONW_PATH=%%i"
if "!PYTHONW_PATH!"=="" set "PYTHONW_PATH=python"

:: Get icon path
set "ICON_PATH=%SCRIPT_DIR%assets\icon.ico"
if not exist "!ICON_PATH!" set "ICON_PATH=%SCRIPT_DIR%assets\icon.png"

:: Create desktop shortcut via PowerShell
powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s = $ws.CreateShortcut('%SHORTCUT%');" ^
  "$s.TargetPath = '!PYTHONW_PATH!';" ^
  "$s.Arguments = '\"%SCRIPT_DIR%app.py\"';" ^
  "$s.WorkingDirectory = '%SCRIPT_DIR%';" ^
  "$s.Description = 'AI System Optimizer by Quasif';" ^
  "if (Test-Path '!ICON_PATH!') { $s.IconLocation = '!ICON_PATH!' };" ^
  "$s.Save()" >nul 2>&1

if exist "%SHORTCUT%" (
    echo  [OK] Desktop shortcut created.
) else (
    echo  [WARN] Desktop shortcut failed - you can create it manually.
)

:: Add to Windows startup
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "AISystemOptimizer" /t REG_SZ ^
    /d "\"!PYTHONW_PATH!\" \"%SCRIPT_DIR%app.py\"" ^
    /f >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Added to Windows startup.
) else (
    echo  [WARN] Could not add to startup.
)

echo.
echo  -------------------------------------------------------
:: ============================================================
:: STEP 6 - FINALIZE AI SETTINGS
:: ============================================================
echo [6/6] Finalizing AI configuration...

if exist "%SCRIPT_DIR%_setup_helper.py" (
    %PYTHON_CMD% "%SCRIPT_DIR%_setup_helper.py" configure
) else (
    echo  [WARN] Setup helper not found.
)

echo.
echo  ============================================================
echo    Setup Complete!
echo.
echo    - AI Model : qwen2.5:0.5b  (ultra-fast, low RAM)
echo    - Shortcut : Created on Desktop
echo    - Startup  : Pinned to Windows startup
echo    - Icon     : Custom speed icon
echo.
echo    Launching AI System Optimizer now...
echo  ============================================================
echo.

:: Kill any stale instance before launching fresh
taskkill /F /IM python.exe /FI "WINDOWTITLE eq AI System Optimizer*" >nul 2>&1
taskkill /F /IM pythonw.exe /FI "WINDOWTITLE eq AI System Optimizer*" >nul 2>&1
taskkill /F /IM AISystemOptimizer.exe >nul 2>&1

:: Launch silently with pythonw (no console window)
if "!PYTHONW_PATH!"=="python" (
    start "" pythonw "%SCRIPT_DIR%app.py"
) else (
    start "" "!PYTHONW_PATH!" "%SCRIPT_DIR%app.py"
)

timeout /t 2 /nobreak >nul
echo  App launched! This window will close.
timeout /t 2 /nobreak >nul
exit /b 0
