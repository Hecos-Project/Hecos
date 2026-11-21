@echo off
setlocal enabledelayedexpansion
title HECOS CORE - ACTIVE SESSION RUNNER (Native Text Console)

for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_CYAN=%ESC%[96m"
set "C_MAG=%ESC%[95m"
set "C_YELLOW=%ESC%[93m"
set "C_RED=%ESC%[91m"
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
echo   %C_MAG%HECOS CORE NATIVE TERMINAL%C_RST%   %C_CYAN%v!HECOS_VERSION!%C_RST%
echo %C_CYAN%==============================================================%C_RST%
echo.

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
        set "PYTHON_CMD=python"
    )
)

rem --- Optional ESC-key environment auto-check before starting ---
!PYTHON_CMD! -c "import sys,msvcrt,time; end=time.time()+0.12; run_check=False; exec('while time.time()<end:\n if msvcrt.kbhit() and ord(msvcrt.getch())==27: run_check=True; break\n time.sleep(0.01)'); print('\n[ .. ] Running environment verification...' if run_check else '', end=''); sys.exit(0 if run_check else 1)"
if !ERRORLEVEL! EQU 0 (
    !PYTHON_CMD! hecos\setup_wizard.py --auto
    if !ERRORLEVEL! NEQ 0 (
        echo %C_YELLOW%[WARN]%C_RST% Configuration issue detected. Launching Setup Wizard...
        timeout /t 3 >nul
        call scripts\windows\setup\HECOS_SETUP_WIZARD.bat
    )
)

echo %C_CYAN%[ ^>^> ]%C_RST% Starting interactive terminal...
echo %C_CYAN%[INFO]%C_RST% Press F9 for a Safe Restart of the program.
echo.

set "HECOS_BOOT_MODE=console"
!PYTHON_CMD! hecos\monitor.py
set "RUN_RC=!ERRORLEVEL!"

echo.
echo %C_YELLOW%[WARN]%C_RST% Process terminated ^(exit code !RUN_RC!^).
pause
exit /b !RUN_RC!
