@echo off
title ZENTRA — Native Web Server (Watchdog)
color 0A

echo.
set /p ZENTRA_VERSION=<core\version
echo  ======================================
echo   ZENTRA NATIVE WEB INTERFACE v%ZENTRA_VERSION%
echo  ======================================
echo.

:: Attiva ambiente virtuale se esiste
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [!] Avvio monitor di controllo in modalità WEB...
echo [!] Apertura automatica del browser in corso...
echo.

:: Apri porta 7070 nel Firewall Windows (solo se la regola non esiste gia')
netsh advfirewall firewall show rule name="Zentra WebUI LAN" >nul 2>&1
if errorlevel 1 (
  echo [*] Apertura porta 7070 nel Firewall Windows...
  netsh advfirewall firewall add rule name="Zentra WebUI LAN" dir=in action=allow protocol=TCP localport=7070 >nul
  echo [+] Porta 7070 aperta. Raggiungibile su http://192.168.1.35:7070/chat
) else (
  echo [+] Regola firewall gia' presente. Porta 7070 attiva.
)
echo.

:: Avviamo il monitor passando il modulo del server web standalone.
python monitor.py --script plugins.web_ui.server


echo.
echo [!] Watchdog terminato.
timeout /t 5
