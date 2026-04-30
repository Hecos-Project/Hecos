@echo off
echo ==================================================
echo   HECOS CORE - ENABLE TRAY AUTOSTART
echo ==================================================
echo.

:: Determine paths
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\..\.."
set HECOS_ROOT=%CD%

set TRAY_RUNNER=%HECOS_ROOT%\scripts\windows\run\HECOS_TRAY_WIN.bat

if not exist "%TRAY_RUNNER%" (
    echo [!] ERROR: Could not find HECOS_TRAY_WIN.bat at:
    echo     %TRAY_RUNNER%
    pause
    exit /b 1
)

echo [*] Adding Hecos Tray to Current User Autostart...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /t REG_SZ /d "\"%TRAY_RUNNER%\"" /f

echo.
echo [+] Done! The Hecos Tray Icon will now launch automatically
echo     every time you log into Windows.
echo.
pause
