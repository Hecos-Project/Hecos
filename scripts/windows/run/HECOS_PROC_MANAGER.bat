@echo off
@chcp 65001 >nul
title HECOS PROCESS MANAGER
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"
color 0D

echo.
set HECOS_VERSION=Unknown
if exist hecos\core\version set /p HECOS_VERSION=<hecos\core\version
echo  ==============================================================
echo   HECOS PROCESS MANAGER v%HECOS_VERSION%
echo  ==============================================================
echo.

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [*] Starting standalone process monitor...
echo.

python scripts\utils\hecos_proc_manager.py

echo.
echo [!] Process terminated.
pause
