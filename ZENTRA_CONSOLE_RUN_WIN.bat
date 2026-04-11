@echo off
title ZENTRA CORE - ACTIVE SESSION RUNNER (Native Text Console)
cd /d "%~dp0"


echo.
set ZENTRA_VERSION=Unknown
if exist zentra\core\version set /p ZENTRA_VERSION=<zentra\core\version
echo  ==============================================================
echo   ZENTRA CORE NATIVE TERMINAL v%ZENTRA_VERSION%
echo  ==============================================================
echo.

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [*] Starting interactive terminal...
echo [*] Press F9 for a Safe Restart of the program.
echo.

python zentra\monitor.py

echo.
echo [!] Process terminated.
pause