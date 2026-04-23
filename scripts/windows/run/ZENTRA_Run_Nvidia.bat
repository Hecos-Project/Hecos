@echo off
@chcp 65001 >nul
title ZENTRA CORE - NVIDIA AI ACCELERATED
cd /d "%~dp0.."
color 0E

echo.
set ZENTRA_VERSION=Unknown
if exist zentra\core\version set /p ZENTRA_VERSION=<zentra\core\version
echo  ==============================================================
echo   ZENTRA CORE NVIDIA RUNNER v%ZENTRA_VERSION%
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

python zentra\monitor.py

echo.
echo [!] Process terminated.
pause