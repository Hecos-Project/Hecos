@echo off
title ZENTRA -- Native Web Server (Watchdog)
color 0B

echo.
set ZENTRA_VERSION=Unknown
if exist core\version set /p ZENTRA_VERSION=<core\version
echo  ==============================================================
echo   ZENTRA NATIVE WEB INTERFACE v%ZENTRA_VERSION%
echo  ==============================================================
echo.

:: Attiva ambiente virtuale se esiste
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [!] Avvio monitor di controllo in modalita' WEB...
echo [!] Apertura automatica del browser in corso...
echo.

:: Apri porta 7070 nel Firewall Windows (solo se la regola non esiste gia)
netsh advfirewall firewall show rule name="Zentra WebUI LAN" >nul 2>&1
if errorlevel 1 (
  echo [*] Apertura porta 7070 nel Firewall Windows...
  netsh advfirewall firewall add rule name="Zentra WebUI LAN" dir=in action=allow protocol=TCP localport=7070 >nul 2>&1
  echo [+] Porta aperta.
) else (
  echo [+] Regola firewall gia' presente. Porta 7070 attiva.
)
echo.

echo  ==============================================================
echo   [ ACCESSO RAPIDO ]
echo   Se chiudi il browser per sbaglio, usa Ctrl + Clic sui link:
echo.
echo   * Chat:     http://localhost:7070/chat
echo   * Config:   http://localhost:7070/zentra/config/ui
echo   * Drive:    http://localhost:7070/drive
echo  ==============================================================
echo.

:: Avviamo il monitor
python monitor.py --script plugins.web_ui.server

echo.
echo [!] Watchdog terminato.
timeout /t 5
