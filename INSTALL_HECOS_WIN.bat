@echo off
setlocal enabledelayedexpansion
title HECOS CORE - FIRST START
color 0B

echo.
echo  +--------------------------------------------------+
echo  ^|                                                  ^|
echo  ^|          HECOS CORE - INITIAL BOOTSTRAP       ^|
echo  ^|                                                  ^|
echo  +--------------------------------------------------+
echo.

:: 1. Search for Python
echo  [*] Detecting Python...
set PY_FOUND=0

:: Check local environments first
if exist "%CD%\python_env\python.exe" (
    set PY_CMD="%CD%\python_env\python.exe"
    set PY_FOUND=1
    goto :python_check_done
)

if exist "%CD%\venv\Scripts\python.exe" (
    set PY_CMD="%CD%\venv\Scripts\python.exe"
    set PY_FOUND=1
    goto :python_check_done
)

:: Check system python, ignoring WindowsApps alias
for /f "tokens=*" %%i in ('where python 2^>nul') do (
    set "PY_PATH=%%~i"
    if "!PY_PATH:WindowsApps=!"=="!PY_PATH!" (
        set PY_CMD="%%~i"
        set PY_FOUND=1
        goto :python_check_done
    )
)

:python_check_done

:: 2. Missing Python Logic
if !PY_FOUND! equ 0 (
    color 0E
    echo.
    echo  [!] Python not found. Initiating automatic installation...
    echo  [*] Downloading Python 3.11 ^(this may take a few minutes^)...
    
    curl --ssl-no-revoke -L -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    if !errorlevel! neq 0 (
        color 0C
        echo  [-] Failed to download Python.
        echo  Please check your internet connection or install manually.
        pause
        exit /b 1
    )
    
    echo  [*] Installing Python ^(quiet mode^)...
    start /wait "" python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1
    
    if !errorlevel! neq 0 (
        color 0C
        echo  [-] Python installation failed.
        pause
        exit /b 1
    )
    
    echo  [+] Python installed successfully.
    if exist python_installer.exe del python_installer.exe
    
    :: Locate installed Python
    if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
        set PY_CMD="%LocalAppData%\Programs\Python\Python311\python.exe"
        set PY_FOUND=1
    ) else if exist "C:\Program Files\Python311\python.exe" (
        set PY_CMD="C:\Program Files\Python311\python.exe"
        set PY_FOUND=1
    ) else (
        echo  [-] Cannot find python.exe after installation.
        echo  Please restart the script to detect it.
        pause
        exit /b 1
    )
    color 0B
    echo.
)

:: 3. Launch Setup Wizard
echo  [+] Python detected: !PY_CMD!
echo  [*] Launching Hecos Setup Wizard...
echo.

!PY_CMD! hecos\setup_wizard.py --web

if %errorlevel% neq 0 (
    echo.
    echo  [-] Setup Wizard ended with errors.
    pause
) else (
    echo.
    echo  +--------------------------------------------------+
    echo  ^|                                                  ^|
    echo  ^|     HECOS INSTALLATION COMPLETE!              ^|
    echo  ^|                                                  ^|
    echo  +--------------------------------------------------+
    echo.
    echo  [*] Checking for Tesseract OCR...
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo  [+] Tesseract OCR found.
    ) else (
        echo  [-] Tesseract OCR not found in default path ^(C:\Program Files\Tesseract-OCR\tesseract.exe^).
        echo      If you want to use the text-clicking features, please install it from:
        echo      https://github.com/UB-Mannheim/tesseract/wiki
    )
    echo.
    echo  [*] Checking for Microsoft Visual C++ Redistributable...
    reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" /v Installed >nul 2>&1
    if !errorlevel! equ 0 (
        echo  [+] Microsoft Visual C++ Redistributable found.
    ) else (
        echo  [-] Microsoft Visual C++ Redistributable might be missing.
        echo      Please install it if you experience issues running Hecos.
    )
    echo.
    echo  HOW TO START HECOS:
    echo.
    echo  1. Look at the BOTTOM-RIGHT corner of your taskbar
    echo     ^(near the system clock^). Click the arrow to
    echo     expand hidden icons if needed.
    echo.
    echo  2. RIGHT-CLICK the Hecos tray icon.
    echo.
    echo  3. Click  [▶ Start Core]  to launch the AI engine.
    echo.
    echo  TIP: The tray icon will start automatically at
    echo       every Windows login from now on.
    echo.
    echo  You can close this window. Hecos runs in background.
    echo.
    pause
)
