@echo off
setlocal enabledelayedexpansion
title Hecos Uninstaller
color 0C

echo ==============================================================================
echo                      HECOS CORE - UNINSTALLER
echo ==============================================================================
echo.

set MODE=%~1

if "%MODE%"=="" (
    echo Scegli una modalita di disinstallazione:
    echo.
    echo 1. Rimuovi solo il Core Hecos (mantiene ambiente Python, Piper)
    echo 2. Rimuovi Core + Dipendenze (elimina venv e packages)
    echo 3. Reset Completo (Rimuove TUTTO: Hecos, Python Embedded e Piper TTS)
    echo.
    set /p CH="Scelta (1/2/3): "
    if "!CH!"=="1" set MODE=--core
    if "!CH!"=="2" set MODE=--deps
    if "!CH!"=="3" set MODE=--full
)

if "%MODE%"=="" (
    echo [!] Nessuna scelta valida. Uscita.
    pause
    exit /b 1
)

echo.
echo ATTENZIONE: La disinstallazione chiudera forzatamente Hecos.
echo Modalita selezionata: %MODE%
echo Premi un tasto per confermare o chiudi questa finestra per annullare.
pause

pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd

echo.
echo [*] Chiusura processi Hecos attivi...
taskkill /F /IM hecos_tray.exe >nul 2>&1
taskkill /F /IM hecos_dashboard.exe >nul 2>&1
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Hecos*" >nul 2>&1

echo [*] Rimozione autostart dal registro...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "HecosTray" /f >nul 2>&1

echo [*] Rimuovendo il Core Hecos...
if exist "%ROOT_DIR%\hecos" rmdir /s /q "%ROOT_DIR%\hecos"
if exist "%ROOT_DIR%\hecos_tray_settings.json" del /q "%ROOT_DIR%\hecos_tray_settings.json"
if exist "%ROOT_DIR%\hecos_update_sources.json" del /q "%ROOT_DIR%\hecos_update_sources.json"
if exist "%ROOT_DIR%\scripts\windows\run\HECOS_TRAY_WIN.bat" del /q "%ROOT_DIR%\scripts\windows\run\HECOS_TRAY_WIN.bat"

if "%MODE%"=="--core" goto :DONE

echo [*] Rimuovendo le dipendenze Python (venv)...
if exist "%ROOT_DIR%\venv" rmdir /s /q "%ROOT_DIR%\venv"

if "%MODE%"=="--deps" goto :DONE

echo [*] Rimuovendo Python Embedded e Piper TTS...
if exist "%ROOT_DIR%\python_env" rmdir /s /q "%ROOT_DIR%\python_env"
if exist "%ROOT_DIR%\bin" rmdir /s /q "%ROOT_DIR%\bin"

:DONE
echo.
echo ==============================================================================
echo [+] Disinstallazione completata con successo!
echo ==============================================================================
echo Se hai scelto il Reset Completo, ora puoi eliminare in sicurezza 
echo l'intera cartella Hecos dal tuo PC.
echo.
pause
