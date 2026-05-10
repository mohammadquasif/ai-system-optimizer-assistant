@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: AI System Optimizer Assistant - Full Auto-Setup v1.1
:: Author: Mohammad Quasif, DBA (AI) | B.Tech (CS)
:: GitHub: https://github.com/mohammadquasif/ai-system-optimizer-assistant
:: License: Personal Use Only (Non-Commercial)
::
:: STRICTLY uses qwen2.5:0.5b only - no larger models
:: ============================================================

title AI System Optimizer - Setup v1.1
color 0B
cls

echo.
echo  =======================================================
echo    AI System Optimizer Assistant v1.0.0
echo    by Mohammad Quasif (DBA AI, B.Tech CS)
echo    github.com/mohammadquasif/ai-system-optimizer-assistant
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
set "TARGET_MODEL=qwen2.5:0.5b"
set "DB_PATH=%SCRIPT_DIR%config\app_data.db"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: ============================================================
:: STEP 0 - CHECK & FIX STALE SETTINGS (only if wrong model)
:: ============================================================
echo [0/7] Checking AI configuration...
echo.

:: Only patch DB if the wrong model is saved - not every time
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python -c "
import sqlite3, os
db = r'%DB_PATH%'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    row = conn.execute(\"SELECT value FROM settings WHERE key='ollama_model'\").fetchone()
    model = row[0] if row else ''
    if model and 'qwen2.5:0.5' not in model:
        conn.execute(\"INSERT OR REPLACE INTO settings (key,value) VALUES ('ai_provider','ollama')\")
        conn.execute(\"INSERT OR REPLACE INTO settings (key,value) VALUES ('ollama_model','qwen2.5:0.5b')\")
        conn.commit()
        print('  [FIX] Stale model corrected: was [' + model + '] -> qwen2.5:0.5b')
    elif not model:
        print('  [INFO] No model saved yet - will be set on first run.')
    else:
        print('  [OK] Model already correct: ' + model)
    conn.close()
else:
    print('  [INFO] DB not found - will be created on first run.')
" 2>nul
) else (
    echo  [INFO] Python not found yet - will be configured after install.
)

echo.
echo  -------------------------------------------------------

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

if exist "%OFFLINE_OLLAMA%" (
    echo  Found offline installer. Installing Ollama...
    "%OFFLINE_OLLAMA%" /S
    timeout /t 5 /nobreak >nul
    echo  [OK] Ollama installed from offline package.
    goto :start_ollama_service
)

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
    timeout /t 8 /nobreak >nul
    if not exist "%SCRIPT_DIR%installer\ollama\" mkdir "%SCRIPT_DIR%installer\ollama\"
    copy "%OLLAMA_INSTALLER%" "%OFFLINE_OLLAMA%" >nul 2>&1
    echo  [OK] Ollama installed.
) else (
    echo  [WARN] Ollama download failed. App will run without AI.
)
goto :step4

:start_ollama_service
echo  Checking if Ollama service is running...
curl -s --max-time 3 http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Starting Ollama service in background...
    start "" /B ollama serve
    timeout /t 5 /nobreak >nul
    echo  [OK] Ollama service started.
) else (
    echo  [OK] Ollama service is already running.
)

:step4
echo.
echo  -------------------------------------------------------

:: ============================================================
:: STEP 4 - AI MODEL: ONLY qwen2.5:0.5b
:: ============================================================
echo [4/7] Checking AI model (target: %TARGET_MODEL% only)...
echo.

set "MODEL_FOUND=0"

ollama --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [SKIP] Ollama not available. Skipping model check.
    goto :step5
)

:: Check STRICTLY for 0.5b only
ollama list 2>nul | findstr /i "qwen2.5:0.5" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "MODEL_FOUND=1"
    echo  [OK] qwen2.5:0.5b is already installed. No download needed.
    goto :step5
)

:: Not found - pull it
echo  [INFO] qwen2.5:0.5b not installed.
echo.

:: Check if Ollama API is reachable before pulling
curl -s --max-time 3 http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [WARN] Ollama service not responding.
    echo         The app will pull qwen2.5:0.5b automatically on first launch.
    goto :step5
)

ping -n 1 8.8.8.8 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [WARN] No internet. App will pull model when connected.
    goto :step5
)

echo  Downloading qwen2.5:0.5b (~400 MB). Please wait...
echo  Note: This is a one-time download. The model is stored locally.
echo.
ollama pull qwen2.5:0.5b
if %ERRORLEVEL% EQU 0 (
    echo  [OK] qwen2.5:0.5b downloaded and ready.
) else (
    echo  [WARN] Model download failed. App will retry on first launch.
)

:step5
echo.
echo  -------------------------------------------------------

:: ============================================================
:: STEP 5 - DESKTOP SHORTCUT
:: ============================================================
echo [5/7] Creating desktop shortcut...
echo.

:: Find icon file
set "ICON_PATH=%SCRIPT_DIR%assets\icon.ico"
if not exist "%ICON_PATH%" set "ICON_PATH=%SCRIPT_DIR%assets\icon.png"

powershell -NoProfile -Command "& { $ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = 'pythonw'; $s.Arguments = '\"%SCRIPT_DIR%app.py\"'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'AI System Optimizer by Mohammad Quasif'; if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' }; $s.Save() }" 2>nul

if exist "%SHORTCUT%" (
    echo  [OK] Desktop shortcut created with custom icon.
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
:: STEP 7 - DB SETTINGS RESET (enforce 0.5b after package install)
:: ============================================================
echo [7/7] Finalizing AI configuration...
echo.

%PYTHON_CMD% -c "
import sqlite3, os, sys
sys.path.insert(0, r'%SCRIPT_DIR%')
try:
    from config.settings import init_db, set_setting, DB_PATH
    init_db()
    set_setting('ai_provider', 'ollama')
    set_setting('ollama_model', 'qwen2.5:0.5b')
    set_setting('first_run', 'false')
    print('  [OK] AI settings locked to qwen2.5:0.5b')
except Exception as e:
    print(f'  [WARN] Could not update DB: {e}')
" 2>&1

echo.
echo  =========================================================
echo    Setup Complete!
echo.
echo    Configuration:
echo    - AI Model: qwen2.5:0.5b (ultra-fast, low RAM)
echo    - Taskbar icon: custom speed optimizer icon
echo    - Auto-start: enabled on Windows startup
echo.
echo    Launching AI System Optimizer now...
echo  =========================================================
echo.

start "" pythonw "%SCRIPT_DIR%app.py"

timeout /t 2 /nobreak >nul
echo  App launched!
echo.
echo  Press any key to close this window...
pause >nul
exit /b 0
