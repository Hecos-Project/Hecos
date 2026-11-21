@echo off
setlocal enabledelayedexpansion

for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_CYAN=%ESC%[96m"
set "C_MAG=%ESC%[95m"
set "C_GREEN=%ESC%[92m"
set "C_RED=%ESC%[91m"
set "C_RST=%ESC%[0m"

echo %C_CYAN%==================================================%C_RST%
echo   %C_MAG%HECOS CORE - ENABLE TRAY AUTOSTART%C_RST%
echo %C_CYAN%==================================================%C_RST%
echo.

rem --- Determine Hecos Core root ---
pushd "%~dp0..\..\.."
set "HECOS_ROOT=!CD!"
popd

rem --- Smart Tray detection: env -> install.toml -> sibling -> C:\Hecos-Tray ---
set "TRAY_DIR="
if not "%HECOS_TRAY_DIR%"=="" (
    if exist "%HECOS_TRAY_DIR%\START_HECOS_TRAY_WIN.bat" set "TRAY_DIR=%HECOS_TRAY_DIR%"
)
if "!TRAY_DIR!"=="" (
    set "REG_FILE=%LOCALAPPDATA%\Hecos\install.toml"
    if exist "!REG_FILE!" (
        for /f "usebackq tokens=1,* delims==" %%K in ("!REG_FILE!") do (
            set "RK=%%~K"
            set "RV=%%~L"
            set "RK=!RK: =!"
            if /i "!RK!"=="tray_path" (
                set "RV=!RV:'=!"
                if "!RV:~0,1!"==" " set "RV=!RV:~1!"
                if exist "!RV!\START_HECOS_TRAY_WIN.bat" set "TRAY_DIR=!RV!"
            )
        )
    )
)
if "!TRAY_DIR!"=="" (
    for %%P in ("!HECOS_ROOT!\..") do (
        set "HECOS_PARENT=%%~fP"
        if "!HECOS_PARENT:~-1!"=="\" set "HECOS_PARENT=!HECOS_PARENT:~0,-1!"
        if exist "!HECOS_PARENT!\Hecos-Tray\START_HECOS_TRAY_WIN.bat" set "TRAY_DIR=!HECOS_PARENT!\Hecos-Tray"
    )
)
if "!TRAY_DIR!"=="" (
    if exist "C:\Hecos-Tray\START_HECOS_TRAY_WIN.bat" set "TRAY_DIR=C:\Hecos-Tray"
)

if "!TRAY_DIR!"=="" (
    echo %C_RED%[FAIL]%C_RST% Could not find Hecos-Tray ^(START_HECOS_TRAY_WIN.bat^).
    if /i not "%~1"=="--silent" pause
    exit /b 1
)

set "TRAY_RUNNER=!TRAY_DIR!\START_HECOS_TRAY_WIN.bat"

echo %C_CYAN%[ .. ]%C_RST% Cleaning legacy Windows registry autostart entries...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraTray" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraCore" /f >nul 2>&1

echo %C_CYAN%[ .. ]%C_RST% Registering Hecos Tray in Windows Startup folder...
echo        Target: !TRAY_RUNNER!
set "PS_TRAY_RUNNER=!TRAY_RUNNER!"
set "PS_TRAY_DIR=!TRAY_DIR!"
powershell -NoProfile -NonInteractive -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut(\"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\HecosTray.lnk\"); $s.TargetPath = $env:PS_TRAY_RUNNER; $s.Arguments = '--silent'; $s.WorkingDirectory = $env:PS_TRAY_DIR; $s.WindowStyle = 7; $ico = Join-Path $env:PS_TRAY_DIR 'assets\Hecos_Logo_SQR_NBG_LogoOnly.ico'; if (Test-Path $ico) { $s.IconLocation = \"$ico,0\" }; $s.Description = 'Hecos System Tray'; $s.Save()"
if !ERRORLEVEL! NEQ 0 (
    echo %C_RED%[FAIL]%C_RST% Failed to create Windows Startup shortcut.
    if /i not "%~1"=="--silent" pause
    exit /b 1
)

echo.
echo %C_GREEN%[ OK ]%C_RST% Hecos Tray will now launch automatically at Windows login.
echo.
if /i not "%~1"=="--silent" pause
exit /b 0
