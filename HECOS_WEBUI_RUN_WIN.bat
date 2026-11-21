@echo off
setlocal enabledelayedexpansion
title HECOS -- Native Web Server (Watchdog)

for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_CYAN=%ESC%[96m"
set "C_MAG=%ESC%[95m"
set "C_GREEN=%ESC%[92m"
set "C_YELLOW=%ESC%[93m"
set "C_RED=%ESC%[91m"
set "C_DIM=%ESC%[90m"
set "C_RST=%ESC%[0m"

rem --- Determine ROOT directory dynamically ---
if exist "%~dp0hecos\core\version" (
    set "ROOT_DIR=%~dp0"
    if "!ROOT_DIR:~-1!"=="\" set "ROOT_DIR=!ROOT_DIR:~0,-1!"
) else if exist "%~dp0..\..\..\hecos\core\version" (
    pushd "%~dp0..\..\.."
    set "ROOT_DIR=!CD!"
    popd
) else (
    set "ROOT_DIR=C:\Hecos"
)
cd /d "!ROOT_DIR!"

echo.
set "HECOS_VERSION=Unknown"
if exist "hecos\core\version" set /p HECOS_VERSION=<"hecos\core\version"
echo %C_CYAN%==============================================================%C_RST%
echo   %C_MAG%HECOS NATIVE WEB INTERFACE%C_RST%   %C_CYAN%v!HECOS_VERSION!%C_RST%
echo %C_CYAN%==============================================================%C_RST%
echo.

rem --- Detect Python BEFORE running helper one-liners ---
set "PYTHON_CMD="
if exist "!ROOT_DIR!\python_env\python.exe" (
    set PYTHON_CMD="!ROOT_DIR!\python_env\python.exe"
) else if exist "!ROOT_DIR!\venv\Scripts\python.exe" (
    set PYTHON_CMD="!ROOT_DIR!\venv\Scripts\python.exe"
) else (
    py -3 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_CMD=py -3"
    ) else (
        python --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 set "PYTHON_CMD=python"
    )
)

if "!PYTHON_CMD!"=="" (
    echo %C_RED%[FAIL]%C_RST% Python not found. Please run HECOS_SETUP_WIZARD.bat first.
    pause
    exit /b 1
)

echo %C_CYAN%[ .. ]%C_RST% Starting control monitor in WEB mode...
echo %C_CYAN%[ .. ]%C_RST% Opening browser automatically...
echo.

rem --- Open port 7070 in Windows Firewall if rule is missing ---
netsh advfirewall firewall show rule name="Hecos WebUI LAN" >nul 2>&1
if errorlevel 1 (
    echo %C_CYAN%[ .. ]%C_RST% Opening port 7070 in Windows Firewall...
    netsh advfirewall firewall add rule name="Hecos WebUI LAN" dir=in action=allow protocol=TCP localport=7070 >nul 2>&1
    echo %C_GREEN%[ OK ]%C_RST% Firewall rule configured.
) else (
    echo %C_GREEN%[ OK ]%C_RST% Firewall rule already active ^(port 7070^).
)
echo.

rem --- Retrieve machine LAN IP and HTTP/HTTPS scheme using detected Python ---
set "LAN_IP=localhost"
for /f "delims=" %%I in ('!PYTHON_CMD! -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254', 1)); print(s.getsockname()[0])" 2^>nul') do set "LAN_IP=%%I"

set "SCHEME=http"
for /f "delims=" %%S in ('!PYTHON_CMD! -c "import yaml; print('https' if yaml.safe_load(open('hecos/config/data/system.yaml', encoding='utf-8')).get('plugins',{}).get('WEB_UI',{}).get('https_enabled',False) else 'http')" 2^>nul') do set "SCHEME=%%S"

echo %C_CYAN%==============================================================%C_RST%
echo   %C_MAG%[ QUICK ACCESS ]%C_RST%
echo   %C_DIM%Connect from this PC, phone, or tablet on your LAN:%C_RST%
echo.
echo   * Chat:     %C_GREEN%!SCHEME!://!LAN_IP!:7070/chat%C_RST%
echo   * Config:   %C_GREEN%!SCHEME!://!LAN_IP!:7070/hecos/config/ui%C_RST%
echo   * Drive:    %C_GREEN%!SCHEME!://!LAN_IP!:7070/drive%C_RST%
echo.
if /i "!SCHEME!"=="https" (
    echo   %C_YELLOW%[INFO]%C_RST% HTTPS Active: Certificates managed by internal PKI.
    echo   %C_DIM%       Root CA: hecos/core/security/pki/ca.pem%C_RST%
)
echo %C_CYAN%==============================================================%C_RST%
echo.

rem --- Start the monitor ---
set "HECOS_BOOT_MODE=webui"
!PYTHON_CMD! hecos\monitor.py --script hecos.modules.web_ui.server
set "RUN_RC=!ERRORLEVEL!"

echo.
echo %C_YELLOW%[WARN]%C_RST% Watchdog terminated ^(exit code !RUN_RC!^).
timeout /t 5
exit /b !RUN_RC!
