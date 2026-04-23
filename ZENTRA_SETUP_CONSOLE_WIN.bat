@echo off
setlocal enabledelayedexpansion
title ZENTRA CORE - SETUP WIZARD
cd /d "%~dp0"

echo.
echo =======================================================
echo   AVVIO ZENTRA SETUP WIZARD...
echo =======================================================
echo.

:: Priority to the isolated portable python runtime
set PYTHON_CMD=python
if exist "%CD%\python_env\python.exe" (
  set PYTHON_CMD="%CD%\python_env\python.exe"
) else if exist "venv\Scripts\python.exe" (
  set PYTHON_CMD="%CD%\venv\Scripts\python.exe"
) else if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

%PYTHON_CMD% zentra\setup_wizard.py

echo.
pause
