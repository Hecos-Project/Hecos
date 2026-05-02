@echo off
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\..\.."

@REM Starts the Hecos System Tray Orchestrator quietly
start "" /b pythonw -m hecos.tray.tray_app
