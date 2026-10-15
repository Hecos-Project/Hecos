@echo off
echo ==================================================
echo   HECOS CORE - DISABLE TRAY AUTOSTART
echo ==================================================
echo.

echo [*] Removing Hecos Tray shortcut from Startup folder...
set "STARTUP_LNK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\HecosTray.lnk"
if exist "%STARTUP_LNK%" (
    del /f /q "%STARTUP_LNK%" 2>nul
)

echo [*] Removing any legacy registry Run keys...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraTray" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "ZentraCore" /f 2>nul

echo.
echo [+] Done! Hecos Tray has been removed from Windows autostart.
echo.
if "%~1" neq "--silent" pause
