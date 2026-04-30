@echo off
setlocal enabledelayedexpansion
title HECOS CORE - ACTIVE SESSION RUNNER (Native Text Console)
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"

echo.
set HECOS_VERSION=Unknown
if exist hecos\core\version set /p HECOS_VERSION=<hecos\core\version
echo  ==============================================================
echo   HECOS CORE NATIVE TERMINAL v%HECOS_VERSION%
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

if not defined PYTHON_CMD set PYTHON_CMD=python
:: Auto-check environment before starting
echo [*] Verifica configurazione ambiente...
!PYTHON_CMD! hecos\setup_wizard.py --auto
if %ERRORLEVEL% NEQ 0 (
  echo [!] Problema di configurazione rilevato.
  echo [!] Lancio del Setup Wizard riparatore...
  timeout /t 3
  call scripts\windows\setup\HECOS_SETUP_CONSOLE_WIN.bat
)

echo [*] Starting interactive terminal...
echo [*] Press F9 for a Safe Restart of the program.
echo.

!PYTHON_CMD! hecos\monitor.py

echo.
echo [!] Process terminated.
pause