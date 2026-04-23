@echo off
setlocal enabledelayedexpansion
title ZENTRA -- Native Web Server (Watchdog)
color 0B

echo.
set ZENTRA_VERSION=Unknown
if exist zentra\core\version set /p ZENTRA_VERSION=<zentra\core\version
echo  ==============================================================
echo   ZENTRA NATIVE WEB INTERFACE v%ZENTRA_VERSION%
echo  ==============================================================
echo.

:: Activate virtual environment if it exists
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"

if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [!] Starting control monitor in WEB mode...
echo [!] Opening browser automatically...
echo.

:: Open port 7070 in Windows Firewall (only if rule doesn't exist)
netsh advfirewall firewall show rule name="Zentra WebUI LAN" >nul 2>&1
if errorlevel 1 (
  echo [*] Opening port 7070 in Windows Firewall...
  netsh advfirewall firewall add rule name="Zentra WebUI LAN" dir=in action=allow protocol=TCP localport=7070 >nul 2>&1
  echo [+] Port opened.
) else (
  echo [+] Firewall rule already exists. Port 7070 is active.
)
echo.

:: Retrieve machine IP for remote access
set LAN_IP=localhost
for /f "delims=" %%i in ('python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254', 1)); print(s.getsockname()[0])" 2^>nul') do set LAN_IP=%%i

:: Recupera lo schema HTTP/HTTPS da system.yaml
set SCHEME=http
for /f "delims=" %%s in ('python -c "import yaml; print('https' if yaml.safe_load(open('zentra/config/data/system.yaml')).get('plugins',{}).get('WEB_UI',{}).get('https_enabled',False) else 'http')" 2^>nul') do set SCHEME=%%s

echo  ==============================================================
echo   [ QUICK ACCESS ]
echo   If you accidentally close the browser or want to
echo   connect from your phone or tablet, use your network address:
echo.
echo   * Chat:     %SCHEME%://%LAN_IP%:7070/chat
echo   * Config:   %SCHEME%://%LAN_IP%:7070/zentra/config/ui
echo   * Drive:    %SCHEME%://%LAN_IP%:7070/drive
echo.
if "%SCHEME%"=="https" (
  echo   [!] HTTPS Active: Certificates are managed by internal PKI.
  echo   [!] Root CA: zentra/core/security/pki/ca.pem
)
echo  ==============================================================
echo.

:: Priority to the isolated portable python runtime
set PYTHON_CMD=python
if exist "python_env\python.exe" (
  set PYTHON_CMD="%ROOT_DIR%\python_env\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set PYTHON_CMD="%ROOT_DIR%\venv\Scripts\python.exe"
)

:: Starting the monitor
!PYTHON_CMD! zentra\monitor.py --script zentra.modules.web_ui.server

echo.
echo [!] Watchdog terminated.
timeout /t 5
