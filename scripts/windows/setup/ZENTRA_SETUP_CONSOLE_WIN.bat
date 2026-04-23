@echo off
setlocal enabledelayedexpansion
title ZENTRA CORE - SETUP WIZARD
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"

echo.
echo =======================================================
echo   AVVIO ZENTRA SETUP WIZARD...
echo =======================================================
echo.

:: Priority to the isolated portable python runtime
set PYTHON_CMD=python
if exist "python_env\python.exe" (
  set PYTHON_CMD="%ROOT_DIR%\python_env\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set PYTHON_CMD="%CD%\venv\Scripts\python.exe"
) else if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

%PYTHON_CMD% zentra\setup_wizard.py

echo.
pause
