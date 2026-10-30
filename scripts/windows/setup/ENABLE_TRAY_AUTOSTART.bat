@echo off
echo ==================================================
echo   HECOS CORE - ENABLE TRAY AUTOSTART
echo ==================================================
echo.

:: Determine paths
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
    if "%~1" neq "--silent" pause
    exit /b 1
)

echo [*] Cleaning legacy Windows registry autostart entries...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraCore" /f 2>nul

echo [*] Registering Hecos Tray in Windows Startup folder...
powershell -NoProfile -NonInteractive -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut(\"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\HecosTray.lnk\"); $s.TargetPath = '%TRAY_RUNNER%'; $s.Arguments = '--silent'; $s.WorkingDirectory = '%TRAY_DIR%'; $s.WindowStyle = 7; if (Test-Path '%TRAY_DIR%\assets\Hecos_Logo_SQR_NBG_LogoOnly.ico') { $s.IconLocation = '%TRAY_DIR%\assets\Hecos_Logo_SQR_NBG_LogoOnly.ico,0' }; $s.Description = 'Hecos System Tray'; $s.Save()"

echo.
echo [+] Done! The Hecos Tray Icon will now launch automatically
echo     every time you log into Windows (Windows 10 / 11 compatible).
echo.
if "%~1" neq "--silent" pause

