@echo off
setlocal enabledelayedexpansion
title Hecos - Portable Setup
color 0B

echo ==============================================================================
echo                      HECOS CORE - PORTABLE INSTALLER
echo ==============================================================================
echo Questo script scarichera e configurera una versione isolata e portatile di 
echo Python e Piper TTS all'interno di questa cartella. Nessuna installazione 
echo globale richiesta sul tuo PC.
echo ==============================================================================
echo.

pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"

:: Versions and URLs
set PYTHON_VERSION=3.11.9
set PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
set PIPER_URL=https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip
set PIPER_VOICE_URL=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/aurora/medium/it_IT-aurora-medium.onnx
set PIPER_VOICE_JSON=https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/aurora/medium/it_IT-aurora-medium.onnx.json

:: Directories
set PYTHON_DIR=%ROOT_DIR%\python_env
set PIPER_DIR=%ROOT_DIR%\bin\piper

:: 1. Download and Configure Portable Python
if not exist "%PYTHON_DIR%\python.exe" (
    echo [*] Downloading Portable Python %PYTHON_VERSION%...
    mkdir "%PYTHON_DIR%" >nul 2>&1
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile 'python.zip'"
    
    echo [*] Extracting Python...
    powershell -Command "Expand-Archive -Path 'python.zip' -DestinationPath '%PYTHON_DIR%' -Force"
    del python.zip

    echo [*] Configuring python._pth to enable site-packages...
    :: Trova il file _pth
    for %%f in ("%PYTHON_DIR%\*._pth") do set PTH_FILE=%%f
    :: Sostituisci #import site con import site
    powershell -Command "(Get-Content '!PTH_FILE!') -replace '#import site', 'import site' | Set-Content '!PTH_FILE!'"
    
    echo [*] Downloading get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"
    
    echo [*] Installing PIP...
    "%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py"
) else (
    echo [+] Portable Python already installed.
)

:: 2. Upgrade pip and install requirements
echo.
echo [*] Installing Hecos dependencies (this may take a few minutes)...
"%PYTHON_DIR%\Scripts\pip.exe" install --upgrade pip
"%PYTHON_DIR%\Scripts\pip.exe" install -r requirements.txt

:: 3. Download Piper TTS
echo.
if not exist "%PIPER_DIR%\piper.exe" (
    echo [*] Downloading Piper TTS...
    if not exist "%ROOT_DIR%\bin" mkdir "%ROOT_DIR%\bin"
    powershell -Command "Invoke-WebRequest -Uri '%PIPER_URL%' -OutFile 'piper.zip'"
    
    echo [*] Extracting Piper TTS...
    powershell -Command "Expand-Archive -Path 'piper.zip' -DestinationPath '%ROOT_DIR%\bin' -Force"
    del piper.zip
    :: A seconda di come è zippato Piper, rinomina la cartella interna o spostala...
    :: Rhasspy's piper windows zip extracts to a folder named "piper" natively.
) else (
    echo [+] Piper TTS already installed.
)

:: 4. Download Default Italian Voice for Piper
echo.
if not exist "%PIPER_DIR%\it_IT-aurora-medium.onnx" (
    echo [*] Downloading Default Voice (Italian: Aurora Medium)...
    powershell -Command "Invoke-WebRequest -Uri '%PIPER_VOICE_URL%' -OutFile '%PIPER_DIR%\it_IT-aurora-medium.onnx'"
    powershell -Command "Invoke-WebRequest -Uri '%PIPER_VOICE_JSON%' -OutFile '%PIPER_DIR%\it_IT-aurora-medium.onnx.json'"
) else (
    echo [+] Default voice already installed.
)

:: 5. Create Desktop Shortcut (Optional UX improvement)
echo.
echo [*] Creating Desktop Shortcut...
set SHORTCUT_SCRIPT=%TEMP%\CreateHecosShortcut.vbs
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%SHORTCUT_SCRIPT%"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Hecos AI.lnk" >> "%SHORTCUT_SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SHORTCUT_SCRIPT%"
echo oLink.TargetPath = "%ROOT_DIR%\scripts\windows\run\HECOS_TRAY_WIN.bat" >> "%SHORTCUT_SCRIPT%"
echo oLink.WorkingDirectory = "%ROOT_DIR%" >> "%SHORTCUT_SCRIPT%"
echo oLink.Description = "Avvia Hecos Tray App" >> "%SHORTCUT_SCRIPT%"
:: Usiamo un'icona di sistema neutra oppure l'exe di Hecos stesso (es python.exe per ora)
echo oLink.IconLocation = "cmd.exe" >> "%SHORTCUT_SCRIPT%"
echo oLink.Save >> "%SHORTCUT_SCRIPT%"
cscript /nologo "%SHORTCUT_SCRIPT%"
del "%SHORTCUT_SCRIPT%"


echo ==============================================================================
echo [SUCCESS] Installazione completata!
echo.
echo Una cartella autonoma per Python e una per Piper sono state create.
echo Sul tuo Desktop e' stato creato un collegamento 'Hecos AI'.
echo.
echo Premi un tasto per avviare Hecos.
echo ==============================================================================
pause

start "" "%ROOT_DIR%\scripts\windows\run\HECOS_TRAY_WIN.bat"
