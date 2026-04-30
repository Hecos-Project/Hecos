@echo off
@chcp 65001 >nul
title HECOS CORE - NVIDIA AI ACCELERATED
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"
color 0E

echo.
set HECOS_VERSION=Unknown
if exist hecos\core\version set /p HECOS_VERSION=<hecos\core\version
echo  ==============================================================
echo   HECOS CORE NVIDIA RUNNER v%HECOS_VERSION%
echo  ==============================================================
echo.

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [*] Starting session with CUDA support...
echo [*] Press F9 for a Safe Restart of the program.
echo.

:: Force CUDA usage if available via environment variables (optional)
set CUDA_VISIBLE_DEVICES=0

python hecos\monitor.py

echo.
echo [!] Process terminated.
pause