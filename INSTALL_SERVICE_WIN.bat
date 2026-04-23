@echo off
setlocal enabledelayedexpansion
title Zentra Core - Service Installer
color 0B

echo.
echo  +--------------------------------------------------+
echo  ^|       ZENTRA CORE - SERVICE INSTALLER            ^|
echo  ^|       Native Modular AI Operating System         ^|
echo  +--------------------------------------------------+
echo.

:: -----------------------------------------------------
:: STEP 1: Auto-elevation to Administrator
:: -----------------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Administrator rights needed. Requesting elevation...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo  [+] Running as Administrator.
echo.

:: -----------------------------------------------------
:: STEP 2: Find Python
:: -----------------------------------------------------
set PYTHON_CMD=python
if exist "%CD%\venv\Scripts\python.exe" (
    set PYTHON_CMD="%CD%\venv\Scripts\python.exe"
    echo  [+] Using virtualenv Python: %PYTHON_CMD%
) else if exist "%CD%\python_env\python.exe" (
    set PYTHON_CMD="%CD%\python_env\python.exe"
    echo  [+] Using portable Python: %PYTHON_CMD%
) else (
    echo  [*] Using system Python.
)
echo.

:: -----------------------------------------------------
:: STEP 3: Install service dependencies
:: -----------------------------------------------------
echo  [*] Installing required packages (pywin32, pystray, pillow)...
%PYTHON_CMD% -m pip install pywin32 pystray pillow --quiet
if %errorlevel% neq 0 (
    echo  [-] Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)
echo  [+] Dependencies installed.
echo.

:: -----------------------------------------------------
:: STEP 4: Run post-install for pywin32 (required!)
:: -----------------------------------------------------
echo  [*] Running pywin32 post-install...
for /f "delims=" %%i in ('%PYTHON_CMD% -c "import site; print(site.getsitepackages()[0])"') do set SITE_PKG=%%i
if exist "%SITE_PKG%\pywin32_system32" (
    %PYTHON_CMD% "%SITE_PKG%\win32\lib\win32timezone.py" >nul 2>&1
)
%PYTHON_CMD% "%SITE_PKG%\win32com\__init__.py" >nul 2>&1

:: -----------------------------------------------------
:: STEP 5: Install the Windows Service
:: -----------------------------------------------------
echo  [*] Registering Zentra Core as a Windows Service...
%PYTHON_CMD% scripts\install_as_service.py --install
if %errorlevel% neq 0 (
    echo  [-] Service installation failed.
    echo  [!] Try running: python scripts\install_as_service.py --install
    pause
    exit /b 1
)
echo.

:: -----------------------------------------------------
:: STEP 6: Launch Tray icon immediately (no reboot needed)
:: -----------------------------------------------------
echo  [*] Starting Zentra Tray icon...

:: Find pythonw (no console window). Fallback to python if pythonw missing.
set PYTHONW_CMD=%PYTHON_CMD:"=%
set PYTHONW_CMD=%PYTHONW_CMD:python.exe=pythonw.exe%
if not exist "%PYTHONW_CMD%" set PYTHONW_CMD=%PYTHON_CMD:"=%

:: Write a tiny VBScript launcher to avoid quote-escaping hell
set VBS_LAUNCHER=%TEMP%\zentra_tray_launch.vbs
(
echo Set oShell = CreateObject("WScript.Shell"^)
echo oShell.CurrentDirectory = "%CD%"
echo oShell.Run """%PYTHONW_CMD%"" -c ""import os,sys; os.chdir(r'%CD%'); sys.path.insert(0,r'%CD%'); from zentra.tray.tray_app import run_tray; run_tray()"" ", 0, False
) > "%VBS_LAUNCHER%"

:: Kill any existing stale tray first, then launch fresh
taskkill /F /FI "WINDOWTITLE eq zentra_core" >nul 2>&1
wscript //nologo "%VBS_LAUNCHER%"
echo  [+] Tray icon launched.
echo.

:: Wait up to 20 seconds for the WebUI to become available, then open the browser
echo  [*] Waiting for Zentra WebUI to become available (up to 20s)...
set ZENTRA_READY=0
for /L %%i in (1,1,20) do (
    if !ZENTRA_READY! == 0 (
        powershell -NonInteractive -Command "try{(New-Object Net.Sockets.TcpClient('127.0.0.1',7070)).Close();exit 0}catch{exit 1}" >nul 2>&1
        if !errorlevel! == 0 ( set ZENTRA_READY=1 ) else ( timeout /t 1 /nobreak >nul )
    )
)

if !ZENTRA_READY! == 1 (
    echo  [+] Zentra is online! Opening WebUI in your browser...
    start "" "http://127.0.0.1:7070/chat"
) else (
    echo  [!] WebUI not ready yet - Zentra may need a moment to initialize.
    echo  [*] The tray icon will open it automatically once ready.
)
echo.

:: -----------------------------------------------------
:: DONE
:: -----------------------------------------------------
echo  +--------------------------------------------------+
echo  ^|   [OK]  Installation Complete!                   ^|
echo  ^|                                                  ^|
echo  ^|   * Zentra Core Windows Service  -^> AUTOMATIC     ^|
echo  ^|     (starts at boot, runs as SYSTEM)             ^|
echo  ^|                                                  ^|
echo  ^|   * Tray Icon  -^> registered in HKCU\Run          ^|
echo  ^|     (auto-starts at user login, no extra admin)  ^|
echo  ^|                                                  ^|
echo  ^|   * Settings: zentra_tray_settings.json          ^|
echo  ^|     service_enabled  : start service on login    ^|
echo  ^|     autoopen_webui   : open browser when online  ^|
echo  ^|     (toggle both from the tray right-click menu) ^|
echo  ^|                                                  ^|
echo  ^|   NOTE: Re-run this installer as Administrator   ^|
echo  ^|   if you reinstall or update Zentra Core.        ^|
echo  ^|                                                  ^|
echo  ^|   To check:  services.msc -^> "Zentra Core"        ^|
echo  ^|   To remove: UNINSTALL_SERVICE_WIN.bat           ^|
echo  +--------------------------------------------------+
echo.
if not "%ZENTRA_SETUP_UNATTENDED%"=="1" pause

