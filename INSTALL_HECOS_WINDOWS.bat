@echo off
setlocal enabledelayedexpansion
title HECOS - OFFICIAL UNIFIED INSTALLER

rem --- Enable ANSI Cyber Colors (Windows 10/11 native VT support) ---
for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_CYAN=%ESC%[96m"
set "C_MAG=%ESC%[95m"
set "C_GREEN=%ESC%[92m"
set "C_YELLOW=%ESC%[93m"
set "C_RED=%ESC%[91m"
set "C_DIM=%ESC%[90m"
set "C_RST=%ESC%[0m"

set "SCRIPT_DIR=%~dp0"
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

echo.
echo %C_CYAN%==============================================================================%C_RST%
echo   %C_MAG%HECOS OFFICIAL UNIFIED INSTALLER%C_RST%   %C_CYAN%(Core + Tray)%C_RST%
echo %C_CYAN%==============================================================================%C_RST%
echo.

rem --- Detect whether we are running INSIDE a Hecos Core folder or STANDALONE ---
set "LOCAL_MODE=0"
if exist "!SCRIPT_DIR!\hecos\setup\web_ui\server.py" (
    set "LOCAL_MODE=1"
    echo %C_GREEN%[ OK ]%C_RST% Local Hecos Core detected at !SCRIPT_DIR!
) else (
    echo %C_CYAN%[ .. ]%C_RST% Standalone bootstrap mode ^(no local files required^)
)

rem --- [1/3] Find ANY compatible Python 3.10+ (or auto-provision Portable 3.11.18) ---
echo %C_CYAN%[1/3] Checking Python bootstrap runtime...%C_RST%
set "PYTHON_CMD="

if "!LOCAL_MODE!"=="1" (
    if exist "!SCRIPT_DIR!\python_env\python.exe" (
        "!SCRIPT_DIR!\python_env\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set PYTHON_CMD="!SCRIPT_DIR!\python_env\python.exe"
            goto PY_READY
        )
    )
)

set "BOOT_PY=%LOCALAPPDATA%\Hecos\bootstrap_py\python.exe"
if exist "!BOOT_PY!" (
    "!BOOT_PY!" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD="!BOOT_PY!"
        goto PY_READY
    )
)

if exist "C:\Hecos\python_env\python.exe" (
    "C:\Hecos\python_env\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD="C:\Hecos\python_env\python.exe"
        goto PY_READY
    )
)

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=py -3"
    goto PY_READY
)

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=python3"
    goto PY_READY
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=python"
    goto PY_READY
)

rem --- Zero-prerequisite auto-provisioning of Portable Python 3.11.18 ---
echo %C_YELLOW%[WARN]%C_RST% No Python 3.10+ found on this PC. Downloading Portable Python 3.11.18 ^(~47 MB^)...
call :PROVISION_BOOTSTRAP_PY "%LOCALAPPDATA%\Hecos\bootstrap_py"
if !ERRORLEVEL! NEQ 0 (
    echo %C_RED%[FAIL]%C_RST% Could not download Portable Python. Check your internet connection and retry.
    pause
    exit /b 1
)
set PYTHON_CMD="%LOCALAPPDATA%\Hecos\bootstrap_py\python.exe"

:PY_READY
for /f "tokens=2 delims= " %%V in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VER=%%V"
echo %C_GREEN%[ OK ]%C_RST% Bootstrap Python ready ^(v!PY_VER!^)

rem --- [2/3] Prepare Graphical Installer UI ---
if "!LOCAL_MODE!"=="1" (
    echo %C_CYAN%[2/3] Using local Setup UI...%C_RST%
    echo %C_CYAN%[3/3] Opening Hecos Graphical Setup Wizard...%C_RST%
    echo.
    cd /d "!SCRIPT_DIR!"
    !PYTHON_CMD! "hecos\setup_wizard.py" --web %*
    exit /b !ERRORLEVEL!
)

echo %C_CYAN%[2/3] Fetching lightweight Graphical Installer UI ^(~80 KB^)...%C_RST%
set "UI_DIR=%TEMP%\hecos_installer_ui"
if exist "!UI_DIR!" rmdir /s /q "!UI_DIR!" >nul 2>&1
mkdir "!UI_DIR!\hecos\setup\web_ui" >nul 2>&1
mkdir "!UI_DIR!\hecos\assets" >nul 2>&1
type nul > "!UI_DIR!\hecos\__init__.py"

set "RAW_BASE=https://raw.githubusercontent.com/Hecos-Project/Hecos/main"
set "DL_FAIL=0"

for %%F in (
    "hecos/setup/__init__.py"
    "hecos/setup/main.py"
    "hecos/setup/i18n.py"
    "hecos/setup/install_registry.py"
    "hecos/setup/utils.py"
    "hecos/setup/unified_installer.py"
    "hecos/setup/web_ui/__init__.py"
    "hecos/setup/web_ui/state.py"
    "hecos/setup/web_ui/styles.py"
    "hecos/setup/web_ui/templates.py"
    "hecos/setup/web_ui/server.py"
) do (
    set "REL=%%~F"
    set "DST=!UI_DIR!\!REL:/=\!"
    call :FETCH_FILE "!RAW_BASE!/!REL!" "!DST!"
    if !ERRORLEVEL! NEQ 0 set "DL_FAIL=1"
)

rem Optional logo (non-fatal if unavailable)
call :FETCH_FILE "!RAW_BASE!/hecos/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" "!UI_DIR!\hecos\assets\Hecos_Logo_SQR_NBG_LogoOnly.png"

if "!DL_FAIL!"=="1" (
    echo %C_RED%[FAIL]%C_RST% Could not download the Hecos Setup UI files from GitHub.
    echo        Check your internet connection or download the full release from:
    echo        https://github.com/Hecos-Project/Hecos/releases/latest
    pause
    exit /b 1
)

echo %C_GREEN%[ OK ]%C_RST% Graphical Installer UI ready.
echo %C_CYAN%[3/3] Opening Hecos Graphical Setup Wizard...%C_RST%
echo.
!PYTHON_CMD! -c "import sys, runpy; sys.path.insert(0, sys.argv[1]); sys.argv = ['hecos.setup.main', '--web', '--standalone']; runpy.run_module('hecos.setup.main', run_name='__main__')" "!UI_DIR!"
set "EXIT_RC=!ERRORLEVEL!"
rmdir /s /q "!UI_DIR!" >nul 2>&1
exit /b !EXIT_RC!


rem ===========================================================================
rem SUBROUTINES
rem ===========================================================================

:FETCH_FILE
set "FF_URL=%~1"
set "FF_DST=%~2"
where curl.exe >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    curl.exe --fail -sSL --retry 2 -o "!FF_DST!" "!FF_URL!" >nul 2>&1
    exit /b !ERRORLEVEL!
)
powershell -NoProfile -NonInteractive -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri $env:FF_URL -OutFile $env:FF_DST -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
exit /b !ERRORLEVEL!

:PROVISION_BOOTSTRAP_PY
set "TARGET_PY=%~1"
set "PBS_ASSET=cpython-3.11.18+20261110-x86_64-pc-windows-msvc-install_only.tar.gz"
set "PBS_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.11.18%%2B20261110-x86_64-pc-windows-msvc-install_only.tar.gz"
set "PBS_SUMS_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20261110/SHA256SUMS"
set "TMP_PY=%TEMP%\hecos_boot_py_%RANDOM%"
set "TMP_TGZ=!TMP_PY!\py.tar.gz"
set "TMP_SUMS=!TMP_PY!\SHA256SUMS"

mkdir "!TMP_PY!" >nul 2>&1
where curl.exe >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    curl.exe --fail -L --retry 3 --progress-bar -o "!TMP_TGZ!" "!PBS_URL!"
) else (
    powershell -NoProfile -NonInteractive -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PBS_URL!' -OutFile '!TMP_TGZ!' -UseBasicParsing"
)
if !ERRORLEVEL! NEQ 0 (
    rmdir /s /q "!TMP_PY!" >nul 2>&1
    exit /b 1
)

rem Verify SHA256 when SHA256SUMS is reachable
where curl.exe >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    curl.exe --fail -sSL --retry 2 -o "!TMP_SUMS!" "!PBS_SUMS_URL!" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "HASH_CHECK_FILE=!TMP_TGZ!"
        set "HASH_SUMS_FILE=!TMP_SUMS!"
        set "HASH_ASSET=!PBS_ASSET!"
        powershell -NoProfile -NonInteractive -Command "$line = Get-Content $env:HASH_SUMS_FILE | Where-Object { $_ -like ('*' + $env:HASH_ASSET) } | Select-Object -First 1; if (-not $line) { exit 2 }; $expected = ($line -split '\s+')[0].Trim().ToLower(); $actual = (Get-FileHash -Algorithm SHA256 $env:HASH_CHECK_FILE).Hash.ToLower(); if ($actual -eq $expected) { exit 0 } else { exit 1 }"
        if !ERRORLEVEL! EQU 1 (
            echo %C_RED%[FAIL]%C_RST% SHA256 checksum mismatch! Aborting.
            rmdir /s /q "!TMP_PY!" >nul 2>&1
            exit /b 1
        )
    )
)

tar -xzf "!TMP_TGZ!" -C "!TMP_PY!"
if !ERRORLEVEL! NEQ 0 (
    rmdir /s /q "!TMP_PY!" >nul 2>&1
    exit /b 1
)
if exist "!TARGET_PY!" rmdir /s /q "!TARGET_PY!" >nul 2>&1
mkdir "!TARGET_PY!" >nul 2>&1
robocopy "!TMP_PY!\python" "!TARGET_PY!" /E /MOVE /NFL /NDL /NJH /NJS /NC /NS /NP >nul 2>&1
rmdir /s /q "!TMP_PY!" >nul 2>&1
if not exist "!TARGET_PY!\python.exe" exit /b 1
exit /b 0
