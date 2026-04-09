@echo off
title ZENTRA CORE - Configuration UI Launcher
color 0E

echo ===================================================
echo           ZENTRA CORE: CONTROL PANEL
echo ===================================================
echo.
echo [SYSTEM] Opening configuration interface...
echo [PATH] http://localhost:7070/zentra/config/ui
echo.

:: Comando per aprire l'URL nel browser predefinito
start http://localhost:7070/zentra/config/ui

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unable to open browser.
    echo Ensure Zentra Core is running on port 7070.
    pause
) else (
    echo [OK] Browser launched successfully.
    timeout /t 3 >nul
)

exit