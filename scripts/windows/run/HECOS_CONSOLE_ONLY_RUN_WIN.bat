@echo off
setlocal enabledelayedexpansion
title HECOS CORE - ACTIVE SESSION RUNNER (Headless Console)
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"

echo.
set HECOS_VERSION=Unknown
if exist hecos\core\version set /p HECOS_VERSION=<hecos\core\version
echo  ==============================================================
echo   HECOS CORE HEADLESS TERMINAL v%HECOS_VERSION%
echo  ==============================================================
echo.
if exist "python_env\python.exe" (
  set PYTHON_CMD="%ROOT_DIR%\python_env\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set PYTHON_CMD="%CD%\venv\Scripts\python.exe"
) else if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
  set PYTHON_CMD=python
)

if not defined PYTHON_CMD (
  py -3 --version >nul 2>&1
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
  ) else (
    set PYTHON_CMD=python
  )
)
:: Auto-check environment before starting
!PYTHON_CMD! -c "import sys,msvcrt,time; end=time.time()+0.12; run_check=False; exec('while time.time()<end:\n if msvcrt.kbhit() and ord(msvcrt.getch())==27: run_check=True; break\n time.sleep(0.01)'); print('\n[*] Running environment verification...' if run_check else '', end=''); sys.exit(0 if run_check else 1)"
if %ERRORLEVEL% EQU 0 (
  !PYTHON_CMD! hecos\setup_wizard.py --auto
  if !ERRORLEVEL! NEQ 0 (
    echo [!] Problema di configurazione rilevato.
    echo [!] Lancio del Setup Wizard riparatore...
    timeout /t 3
    call scripts\windows\setup\HECOS_SETUP_CONSOLE_WIN.bat
  )
)

echo [*] Starting interactive terminal (Headless Mode)...
echo [*] Press F9 for a Safe Restart of the program.
echo.

set HECOS_BOOT_MODE=console
set HECOS_HEADLESS=1
echo 1 > .headless_boot
!PYTHON_CMD! hecos\monitor.py

echo.
echo [!] Process terminated.
pause
