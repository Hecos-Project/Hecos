@echo off
setlocal enabledelayedexpansion
title Zentra Core — Service Installer
color 0B

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║       ZENTRA CORE — SERVICE INSTALLER           ║
echo  ║       Native Modular AI Operating System        ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────────────
:: STEP 1: Auto-elevation to Administrator
:: ─────────────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Administrator rights needed. Requesting elevation...
    echo.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo  [+] Running as Administrator.
echo.

:: ─────────────────────────────────────────────────────
:: STEP 2: Find Python
:: ─────────────────────────────────────────────────────
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

:: ─────────────────────────────────────────────────────
:: STEP 3: Install service dependencies
:: ─────────────────────────────────────────────────────
echo  [*] Installing required packages (pywin32, pystray, pillow)...
%PYTHON_CMD% -m pip install pywin32 pystray pillow --quiet
if %errorlevel% neq 0 (
    echo  [-] Failed to install packages. Check your internet connection.
    pause
    exit /b 1
)
echo  [+] Dependencies installed.
echo.

:: ─────────────────────────────────────────────────────
:: STEP 4: Run post-install for pywin32 (required!)
:: ─────────────────────────────────────────────────────
echo  [*] Running pywin32 post-install...
for /f "delims=" %%i in ('%PYTHON_CMD% -c "import site; print(site.getsitepackages()[0])"') do set SITE_PKG=%%i
if exist "%SITE_PKG%\pywin32_system32" (
    %PYTHON_CMD% "%SITE_PKG%\win32\lib\win32timezone.py" >nul 2>&1
)
%PYTHON_CMD% "%SITE_PKG%\win32com\__init__.py" >nul 2>&1

:: ─────────────────────────────────────────────────────
:: STEP 5: Install the Windows Service
:: ─────────────────────────────────────────────────────
echo  [*] Registering Zentra Core as a Windows Service...
%PYTHON_CMD% scripts\install_as_service.py --install
if %errorlevel% neq 0 (
    echo  [-] Service installation failed.
    echo  [!] Try running: python scripts\install_as_service.py --install
    pause
    exit /b 1
)
echo.

:: ─────────────────────────────────────────────────────
:: DONE
:: ─────────────────────────────────────────────────────
echo  ╔══════════════════════════════════════════════════╗
echo  ║   ✔  Installation Complete!                     ║
echo  ║                                                  ║
echo  ║   • Zentra Core is now registered as a service  ║
echo  ║   • It will start automatically at next login   ║
echo  ║   • Tray icon will appear in the system tray    ║
echo  ║                                                  ║
echo  ║   To check:  services.msc → "Zentra Core"       ║
echo  ║   To remove: UNINSTALL_SERVICE_WIN.bat           ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
