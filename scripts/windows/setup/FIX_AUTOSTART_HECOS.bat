@echo off
echo ==================================================
echo   HECOS CORE - AUTOSTART REPAIR TOOL
echo ==================================================
echo.

:: Determine current Hecos root correctly
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\..\.."
set HECOS_ROOT=%CD%

set TRAY_RUNNER=%HECOS_ROOT%\scripts\windows\run\HECOS_TRAY_WIN.bat

if not exist "%TRAY_RUNNER%" (
    echo [!] ERROR: Could not find HECOS_TRAY_WIN.bat at:
    echo     %TRAY_RUNNER%
    echo.
    echo Please make sure you are running this from the Hecos/scripts/windows/setup folder.
    pause
    exit /b 1
)

echo [*] Cleaning legacy Zentra autostart entries...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraCore" /f 2>nul

echo [*] Registering new Hecos autostart path...
echo     Path: %TRAY_RUNNER%
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /t REG_SZ /d "\"%TRAY_RUNNER%\"" /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [+] SUCCESS: Autostart has been repaired!
    echo     Hecos will now start automatically at login.
) else (
    echo.
    echo [!] ERROR: Failed to update registry. 
    echo     Please try running this script as Administrator.
)

echo.
pause
