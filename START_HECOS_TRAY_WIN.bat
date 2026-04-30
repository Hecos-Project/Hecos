@echo off
setlocal
title Hecos - Restart Tray Icon
color 0B

echo.
echo  [*] Restoring system tray icon...
echo.

:: Detect PythonW (Windowless)
set PYTHONW_CMD=pythonw
if exist "venv\Scripts\pythonw.exe" (
    set PYTHONW_CMD="venv\Scripts\pythonw.exe"
) else if exist "python_env\pythonw.exe" (
    set PYTHONW_CMD="pythonw_env\pythonw.exe"
) else if exist "venv\Scripts\python.exe" (
    set PYTHONW_CMD="venv\Scripts\python.exe"
)

:: Run the tray app in detached mode
start "" %PYTHONW_CMD% -m hecos.tray.tray_app

echo  [+] Command sent. The icon will appear in the system tray.
echo  [!] This window will close in 2 seconds...
echo.
timeout /t 2 >nul
exit
