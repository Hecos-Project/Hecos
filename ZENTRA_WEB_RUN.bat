@echo off
title ZENTRA — Native Web Server
color 0A

echo.
echo  ======================================
echo   ZENTRA NATIVE WEB INTERFACE
echo  ======================================
echo.

:: Attiva ambiente virtuale se esiste
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [!] Avvio server Flask su porta 7070...
echo [!] Apertura automatica del browser in corso...
echo.

:: Avvia il server direttamente nella finestra corrente. 
:: Grazie all'aggiornamento di server.py, il browser si aprirà da solo.
python -m plugins.web_ui.server

echo.
echo Server arrestato.
pause
