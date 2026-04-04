@echo off
@chcp 65001 >nul
title ZENTRA PROCESS MANAGER
cd /d "%~dp0"
color 0D

echo.
set ZENTRA_VERSION=Unknown
if exist core\version set /p ZENTRA_VERSION=<core\version
echo  ==============================================================
echo   ZENTRA PROCESS MANAGER v%ZENTRA_VERSION%
echo  ==============================================================
echo.

:: Attiva l'ambiente virtuale se esiste
if exist "venv\Scripts\activate.bat" (
  call venv\Scripts\activate.bat
)

echo [*] Avvio monitor di controllo processi (standalone)...
echo.

python zentra_proc_manager.py

echo.
echo [!] Processo terminato.
pause
