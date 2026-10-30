@echo off
echo ==================================================
echo   HECOS - AUTOSTART REPAIR TOOL
echo ==================================================
echo.

:: Determine current Hecos root correctly
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\..\.."
set HECOS_ROOT=%CD%

:: Smart Tray detection: exact match first, then search root
set TRAY_RUNNER=%HECOS_ROOT%\..\Hecos-Tray\START_HECOS_TRAY_WIN.bat
if not exist "%TRAY_RUNNER%" (
    if exist "C:\Hecos-Tray\START_HECOS_TRAY_WIN.bat" (
        set TRAY_RUNNER=C:\Hecos-Tray\START_HECOS_TRAY_WIN.bat
    )
)

:: Normalize to full absolute path
for %%F in ("%TRAY_RUNNER%") do set "TRAY_RUNNER=%%~fF"
for %%F in ("%TRAY_RUNNER%\..") do set "TRAY_DIR=%%~fF"

if not exist "%TRAY_RUNNER%" (
    echo [!] ERROR: Could not find START_HECOS_TRAY_WIN.bat at:
    echo     %TRAY_RUNNER%
    echo.
    echo Please make sure you are running this from the Hecos/scripts/windows/setup folder.
    pause
    exit /b 1
)

echo [*] Cleaning legacy Windows registry autostart entries...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraCore" /f 2>nul

echo [*] Registering new Hecos autostart shortcut in Startup folder...
echo     Path: %TRAY_RUNNER%
powershell -NoProfile -NonInteractive -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut(\"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\HecosTray.lnk\"); $s.TargetPath = '%TRAY_RUNNER%'; $s.Arguments = '--silent'; $s.WorkingDirectory = '%TRAY_DIR%'; $s.WindowStyle = 7; if (Test-Path '%TRAY_DIR%\assets\Hecos_Logo_SQR_NBG_LogoOnly.ico') { $s.IconLocation = '%TRAY_DIR%\assets\Hecos_Logo_SQR_NBG_LogoOnly.ico,0' }; $s.Description = 'Hecos System Tray'; $s.Save()"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [+] SUCCESS: Autostart has been repaired!
    echo     Hecos Tray will now start automatically at login (Windows 10 / 11 compatible).
) else (
    echo.
    echo [!] ERROR: Failed to create autostart shortcut.
)

echo.
pause
