@echo off
title HECOS - Configuration UI Launcher
color 0E

echo ===================================================
echo           HECOS: CONTROL PANEL
echo ===================================================
echo.
echo [SYSTEM] Opening configuration interface...
echo [PATH] http://localhost:7070/hecos/config/ui
echo.

:: Comando per aprire l'URL nel browser predefinito
start http://localhost:7070/hecos/config/ui

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Unable to open browser.
    echo Ensure Hecos is running on port 7070.
    pause
) else (
    echo [OK] Browser launched successfully.
    timeout /t 3 >nul
)

exit