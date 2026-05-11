@echo off
setlocal EnableDelayedExpansion

title AI System Optimizer - Setup
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

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: ============================================================
:: STEP 1 - FIND OR INSTALL PYTHON
:: ============================================================
echo [1/2] Checking Python...

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
    echo  [OK] Python !PYVER! found.
    set "PYTHON_CMD=python"
    goto :launch_gui
)

py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Python found via py launcher.
    set "PYTHON_CMD=py"
    goto :launch_gui
)

echo  [!] Python not found. Downloading Python 3.13...
ping -n 1 8.8.8.8 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] No internet connection. Install Python from https://www.python.org then run INSTALL.bat again.
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
    echo  [INFO] Python installed. Please restart your PC then run INSTALL.bat again.
    pause
    exit /b 0
)
set "PYTHON_CMD=python"

:: ============================================================
:: STEP 2 - LAUNCH GUI INSTALLER
:: ============================================================
:launch_gui
echo.
echo [2/2] Launching graphical installer...
echo.

if exist "%SCRIPT_DIR%installer_gui.py" (
    %PYTHON_CMD% "%SCRIPT_DIR%installer_gui.py" %*
    exit /b 0
)

echo  [ERROR] installer_gui.py not found in %SCRIPT_DIR%
echo  Falling back to command-line setup...
echo.
goto :cli_fallback

:: ============================================================
:: CLI FALLBACK (only if installer_gui.py is missing)
:: ============================================================
:cli_fallback
echo [A] Installing Python packages...
%PYTHON_CMD% -m pip install --upgrade pip --quiet --disable-pip-version-check >nul 2>&1

if exist "%SCRIPT_DIR%requirements.txt" (
    echo  Installing from requirements.txt...
    %PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet --no-warn-script-location
    if !ERRORLEVEL! NEQ 0 (
        echo  Retrying with individual packages...
        %PYTHON_CMD% -m pip install PyQt6 psutil pyttsx3 requests cryptography pywin32 winshell openai anthropic httpx schedule APScheduler plyer matplotlib Pillow colorlog pyqtgraph SpeechRecognition --quiet --no-warn-script-location
    )
) else (
    %PYTHON_CMD% -m pip install PyQt6 psutil pyttsx3 requests cryptography pywin32 winshell openai anthropic httpx schedule APScheduler plyer matplotlib Pillow colorlog pyqtgraph SpeechRecognition --quiet --no-warn-script-location
)
echo  [OK] Core packages installed.

echo  Installing PyAudio (voice input)...
%PYTHON_CMD% -m pip install PyAudio --quiet --no-warn-script-location >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo  [OK] PyAudio installed.
) else (
    %PYTHON_CMD% -m pip install pipwin --quiet --no-warn-script-location >nul 2>&1
    %PYTHON_CMD% -m pipwin install pyaudio >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo  [OK] PyAudio installed via pipwin.
    ) else (
        echo  [WARN] PyAudio skipped - voice input disabled.
        echo         To enable: install Microsoft C++ Build Tools then run: pip install PyAudio
    )
)

echo.
echo  [B] Launching app...
set "PYTHONW_PATH="
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do set "PYTHONW_PATH=%%i"
if "!PYTHONW_PATH!"=="" set "PYTHONW_PATH=%PYTHON_CMD%"
start "" "!PYTHONW_PATH!" "%SCRIPT_DIR%app.py"
exit /b 0
