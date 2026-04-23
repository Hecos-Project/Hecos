@echo off
setlocal enabledelayedexpansion
title Zentra Core - Service Uninstaller
color 0C

echo.
echo  +--------------------------------------------------+
echo  ^|       ZENTRA CORE - SERVICE UNINSTALLER          ^|
echo  +--------------------------------------------------+
echo.

:: Auto-elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Requesting Administrator elevation...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set PYTHON_CMD=python
if exist "%CD%\venv\Scripts\python.exe" set PYTHON_CMD="%CD%\venv\Scripts\python.exe"
if exist "%CD%\python_env\python.exe"   set PYTHON_CMD="%CD%\python_env\python.exe"

echo  [*] Stopping and removing Zentra Core service...
%PYTHON_CMD% scripts\install_as_service.py --uninstall

echo.
echo  [+] Service removed successfully.
echo  [*] You can still use Zentra manually with ZENTRA_WEB_RUN_WIN.bat
echo.
if not "%ZENTRA_SETUP_UNATTENDED%"=="1" pause
