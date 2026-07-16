@echo off
setlocal

:: Get the directory where the batch file is located
set "DIR=%~dp0"
cd /d "%DIR%"

echo =====================================================================
echo    HECOS SYSTEM UNINSTALLER
echo =====================================================================
echo.
echo Starting Hecos Setup Wizard...
echo Please use the Web Interface to proceed with uninstallation.
echo.

:: We launch the setup wizard normally, user can scroll down to UNINSTALL.
:: We use the existing python environment if running from venv, or global otherwise.

if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" -m hecos.setup.main --web
) else (
    python -m hecos.setup.main --web
)

pause
