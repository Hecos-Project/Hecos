@echo off
setlocal enabledelayedexpansion
title HECOS CORE - FIRST START
color 0B

echo.
echo  +--------------------------------------------------+
echo  ^|                                                  ^|
echo  ^|          HECOS CORE - INITIAL BOOTSTRAP       ^|
echo  ^|                                                  ^|
echo  +--------------------------------------------------+
echo.

:: 1. Search for Python
echo  [*] Detecting Python...
set PY_FOUND=0

where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
    set PY_FOUND=1
)

if !PY_FOUND! equ 0 (
    if exist "%CD%\python_env\python.exe" (
        set PY_CMD="%CD%\python_env\python.exe"
        set PY_FOUND=1
    )
)

if !PY_FOUND! equ 0 (
    if exist "%CD%\venv\Scripts\python.exe" (
        set PY_CMD="%CD%\venv\Scripts\python.exe"
        set PY_FOUND=1
    )
)

:: 2. Missing Python Logic
if !PY_FOUND! equ 0 (
    color 0C
    echo.
    echo  [!] OH NO! PYTHON NOT FOUND.
    echo.
    echo  Hecos is a native AI system and requires Python 3.10 or higher.
    echo.
    echo  HOW TO FIX THIS:
    echo  1. Go to: https://www.python.org/downloads/
    echo  2. Download the latest Python for Windows.
    echo  3. IMPORTANT: When installing, check the box: 
    echo     "[X] Add Python to PATH"
    echo  4. Finish installation and restart this script.
    echo.
    set /p choice="[*] Do you want to open the Python download page now? (y/n): "
    if /i "!choice!"=="y" start https://www.python.org/downloads/
    echo.
    echo  Press any key to exit...
    pause >nul
    exit /b
)

:: 3. Launch Setup Wizard
echo  [+] Python detected: !PY_CMD!
echo  [*] Launching Hecos Setup Wizard...
echo.

!PY_CMD! hecos\setup_wizard.py --web

if %errorlevel% neq 0 (
    echo.
    echo  [-] Setup Wizard ended with errors.
    pause
)
