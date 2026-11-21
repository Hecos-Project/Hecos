@echo off
setlocal enabledelayedexpansion
@chcp 65001 >nul
title HECOS PROCESS MANAGER

for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_CYAN=%ESC%[96m"
set "C_MAG=%ESC%[95m"
set "C_YELLOW=%ESC%[93m"
set "C_RST=%ESC%[0m"

pushd "%~dp0..\..\.."
set "ROOT_DIR=!CD!"
popd
cd /d "!ROOT_DIR!"

echo.
set "HECOS_VERSION=Unknown"
if exist "hecos\core\version" set /p HECOS_VERSION=<"hecos\core\version"
echo %C_CYAN%==============================================================%C_RST%
echo   %C_MAG%HECOS PROCESS MANAGER%C_RST%   %C_CYAN%v!HECOS_VERSION!%C_RST%
echo %C_CYAN%==============================================================%C_RST%
echo.

set "PYTHON_CMD="
if exist "!ROOT_DIR!\python_env\python.exe" (
    set PYTHON_CMD="!ROOT_DIR!\python_env\python.exe"
) else if exist "!ROOT_DIR!\venv\Scripts\python.exe" (
    set PYTHON_CMD="!ROOT_DIR!\venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo %C_CYAN%[ ^>^> ]%C_RST% Starting standalone process monitor...
echo.

!PYTHON_CMD! scripts\utils\hecos_proc_manager.py
set "RUN_RC=!ERRORLEVEL!"

echo.
echo %C_YELLOW%[WARN]%C_RST% Process terminated ^(exit code !RUN_RC!^).
pause
exit /b !RUN_RC!
