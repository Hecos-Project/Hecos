@echo off
@chcp 65001 >nul
title ZENTRA CORE - NVIDIA AI ACCELERATED
cd /d "%~dp0"
color 0E

echo.
set ZENTRA_VERSION=Unknown
if exist core\version set /p ZENTRA_VERSION=<core\version
echo  ==============================================================
echo   ZENTRA CORE NVIDIA RUNNER v%ZENTRA_VERSION%
echo  ==============================================================
echo.

:: Attiva l'ambiente virtuale se esiste
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [*] Avvio sessione con supporto CUDA...
echo [*] Premere F9 per un Riavvio Sicuro del programma.
echo.

:: Forza l'uso di CUDA se disponibile via variabili d'ambiente (opzionale)
set CUDA_VISIBLE_DEVICES=0

python monitor.py

echo.
echo [!] Processo terminato.
pause