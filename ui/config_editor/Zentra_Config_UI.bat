@echo off
title ZENTRA CORE - Configuration UI Launcher
color 0E

echo ===================================================
echo           ZENTRA CORE: PANNELLO DI CONTROLLO
echo ===================================================
echo.
echo [SISTEMA] Apertura interfaccia di configurazione...
echo [PATH] http://localhost:7070/zentra/config/ui
echo.

:: Comando per aprire l'URL nel browser predefinito
start http://localhost:7070/zentra/config/ui

if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Impossibile aprire il browser.
    echo Assicurati che Zentra Core sia attivo sulla porta 7070.
    pause
) else (
    echo [OK] Browser lanciato con successo.
    timeout /t 3 >nul
)

exit