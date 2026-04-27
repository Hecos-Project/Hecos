@echo off
setlocal
title Zentra Core - Restart Tray Icon
color 0B

echo.
echo  [*] Ripristino icona della barra delle applicazioni (Tray Icon)...
echo.

:: Detect PythonW (Windowless)
set PYTHONW_CMD=pythonw
if exist "venv\Scripts\pythonw.exe" (
    set PYTHONW_CMD="venv\Scripts\pythonw.exe"
) else if exist "python_env\pythonw.exe" (
    set PYTHONW_CMD="python_env\pythonw.exe"
) else if exist "venv\Scripts\python.exe" (
    set PYTHONW_CMD="venv\Scripts\python.exe"
)

:: Run the tray app in detached mode
start "" %PYTHONW_CMD% -m zentra.tray.tray_app

echo  [+] Comando inviato. L'icona apparira' nella barra di sistema.
echo  [!] Questa finestra si chiudera' tra 2 secondi...
echo.
timeout /t 2 >nul
exit
