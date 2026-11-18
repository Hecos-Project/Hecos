@echo off
setlocal enabledelayedexpansion
title HECOS CODING & AIDER STUDIO CLI
if exist "%~dp0hecos\core\version" (
    set "ROOT_DIR=%~dp0"
) else if exist "%~dp0..\..\..\hecos\core\version" (
    pushd "%~dp0..\..\.."
    set "ROOT_DIR=!CD!"
    popd
) else (
    set "ROOT_DIR=C:\Hecos"
)
cd /d "%ROOT_DIR%"

if exist "python_env\python.exe" (
    set PYTHON_CMD="%ROOT_DIR%\python_env\python.exe"
) else (
    set PYTHON_CMD=python
)

set "PATH=%ROOT_DIR%\python_env\Scripts;%ROOT_DIR%\tools\aider_env\Scripts;%PATH%"
set "PYTHONPATH=%ROOT_DIR%"
set "PYTHONIOENCODING=utf-8"

!PYTHON_CMD! -m hecos.modules.executor.cli_bridge.coding_cli_app %*
