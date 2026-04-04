@echo off
title ZENTRA CORE - ACTIVE SESSION RUNNER (Native Text Console)
cd /d "%~dp0"
color 0A

echo.
set ZENTRA_VERSION=Unknown
if exist core\version set /p ZENTRA_VERSION=<core\version
echo  ==============================================================
echo   ZENTRA CORE NATIVE TERMINAL v%ZENTRA_VERSION%
echo  ==============================================================
echo.

:: Attiva l'ambiente virtuale se esiste
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [*] Avvio terminale interattivo...
echo [*] Premere F9 per un Riavvio Sicuro del programma.
echo.

python monitor.py

echo.
echo [!] Processo terminato.
pause