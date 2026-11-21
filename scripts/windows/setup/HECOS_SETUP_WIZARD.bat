@echo off
setlocal enabledelayedexpansion
title HECOS - CORE SETUP WIZARD

rem --- Enable ANSI Cyber Colors (Windows 10/11 native VT support) ---
for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "C_CYAN=%ESC%[96m"
set "C_MAG=%ESC%[95m"
set "C_GREEN=%ESC%[92m"
set "C_YELLOW=%ESC%[93m"
set "C_RED=%ESC%[91m"
set "C_DIM=%ESC%[90m"
set "C_WHITE=%ESC%[97m"
set "C_RST=%ESC%[0m"

rem --- Parse CLI flags: --unattended / --silent, --tray-dir <path>, --web, --doctor ---
set "UNATTENDED=0"
set "ARG_TRAY_DIR="
set "LAUNCH_MODE=menu"

:PARSE_ARGS
if "%~1"=="" goto ARGS_DONE
if /i "%~1"=="--unattended" set "UNATTENDED=1"
if /i "%~1"=="--silent" set "UNATTENDED=1"
if /i "%~1"=="-s" set "UNATTENDED=1"
if /i "%~1"=="--web" set "LAUNCH_MODE=web"
if /i "%~1"=="--gui" set "LAUNCH_MODE=web"
if /i "%~1"=="--doctor" set "LAUNCH_MODE=doctor"
if /i "%~1"=="--tray-dir" (
    set "ARG_TRAY_DIR=%~2"
    shift
)
shift
goto PARSE_ARGS

:ARGS_DONE
if "!UNATTENDED!"=="1" set "LAUNCH_MODE=install"

rem --- Determine ROOT_DIR dynamically ---
set "ROOT_DIR="
if exist "%~dp0..\..\..\hecos\core\version" (
    pushd "%~dp0..\..\.."
    set "ROOT_DIR=!CD!"
    popd
) else if exist "%~dp0hecos\core\version" (
    set "ROOT_DIR=%~dp0"
    if "!ROOT_DIR:~-1!"=="\" set "ROOT_DIR=!ROOT_DIR:~0,-1!"
) else if exist "%~dp0..\Hecos\hecos\core\version" (
    pushd "%~dp0..\Hecos"
    set "ROOT_DIR=!CD!"
    popd
) else (
    set "ROOT_DIR=C:\Hecos"
)

rem --- Setup Wizard Log ---
if not exist "!ROOT_DIR!\logs" mkdir "!ROOT_DIR!\logs" >nul 2>&1
set "SETUP_LOG=!ROOT_DIR!\logs\setup_wizard.log"
echo [%DATE% %TIME%] HECOS CORE SETUP WIZARD STARTED ^(mode=!LAUNCH_MODE!, root=!ROOT_DIR!^) >> "!SETUP_LOG!"

rem --- Read Core version ---
set "CORE_VER=unknown"
if exist "!ROOT_DIR!\hecos\core\version" set /p CORE_VER=<"!ROOT_DIR!\hecos\core\version"

echo.
echo %C_CYAN%==============================================================================%C_RST%
echo   %C_MAG%HECOS CORE SETUP WIZARD%C_RST%   %C_CYAN%v!CORE_VER!%C_RST%
echo %C_CYAN%==============================================================================%C_RST%
echo.

rem ===========================================================================
rem [1/5] PATH SAFETY & SYSTEM CHECK
rem ===========================================================================
echo %C_CYAN%[1/5] Path ^& System Check%C_RST%

call :VALIDATE_PATH "!ROOT_DIR!"
if /i "!PATH_STATUS!"=="ERR" (
    echo %C_RED%[FAIL]%C_RST% Unsafe installation path: !ROOT_DIR!
    echo        Reason: %C_YELLOW%!PATH_MSG!%C_RST%
    echo [%DATE% %TIME%] FAIL unsafe path: !ROOT_DIR! ^(!PATH_MSG!^) >> "!SETUP_LOG!"
    if "!UNATTENDED!"=="1" (
        echo %C_RED%[FAIL]%C_RST% Cannot auto-relocate in unattended mode. Move Hecos to a safe path ^(e.g. C:\Hecos^) and retry.
        exit /b 1
    )
    echo.
    echo   Hecos supports ANY drive or folder, provided the path has no spaces,
    echo   non-ASCII accents, or special shell characters.
    echo.
    set "DEFAULT_TARGET=C:\Hecos"
    echo   Would you like to automatically relocate Hecos to a safe folder now?
    echo   %C_DIM%Press Enter for default [!DEFAULT_TARGET!], type a custom path, or type N to exit.%C_RST%
    echo.
    set "NEW_TARGET="
    set /p NEW_TARGET="  %C_CYAN%>>%C_RST% Target folder [!DEFAULT_TARGET!]: "
    if /i "!NEW_TARGET!"=="N" exit /b 1
    if "!NEW_TARGET!"=="" set "NEW_TARGET=!DEFAULT_TARGET!"
    call :VALIDATE_PATH "!NEW_TARGET!"
    if /i "!PATH_STATUS!"=="ERR" (
        echo %C_RED%[FAIL]%C_RST% Chosen target is also unsafe: !PATH_MSG!
        pause
        exit /b 1
    )
    echo %C_CYAN%[ .. ]%C_RST% Relocating Hecos Core to !NEW_TARGET! ...
    robocopy "!ROOT_DIR!" "!NEW_TARGET!" /E /IS /IT /NFL /NDL /NJH /NJS /NC /NS /NP >nul 2>&1
    if !ERRORLEVEL! GEQ 8 (
        echo %C_RED%[FAIL]%C_RST% Relocation failed. Please move the folder manually to !NEW_TARGET!.
        pause
        exit /b 1
    )
    echo %C_GREEN%[ OK ]%C_RST% Hecos Core relocated to !NEW_TARGET!.
    echo %C_CYAN%[ ^>^> ]%C_RST% Restarting Setup Wizard from the new location...
    echo.
    call "!NEW_TARGET!\scripts\windows\setup\HECOS_SETUP_WIZARD.bat"
    exit /b !ERRORLEVEL!
)

if /i "!PATH_STATUS!"=="WARN" (
    echo %C_YELLOW%[WARN]%C_RST% Path advisory: !PATH_MSG!
) else (
    echo %C_GREEN%[ OK ]%C_RST% Install path verified: !ROOT_DIR!
)

if exist "!ROOT_DIR!\hecos\core\version" (
    echo %C_GREEN%[ OK ]%C_RST% Hecos Core v!CORE_VER! detected
) else (
    echo %C_RED%[FAIL]%C_RST% Core files not found at !ROOT_DIR!
)

rem --- Smart Tray Detection ---
call :DETECT_TRAY
if not "!TRAY_DIR!"=="" (
    echo %C_GREEN%[ OK ]%C_RST% Hecos Tray detected: !TRAY_DIR!
    if "!TRAY_WARN!"=="1" (
        echo %C_YELLOW%[WARN]%C_RST% Tray folder has a version suffix ^(recommended name: Hecos-Tray^)
    )
) else (
    echo %C_DIM%[ -- ]%C_RST% Hecos Tray not detected ^(optional; Core runs standalone too^)
)
echo.

rem ===========================================================================
rem [2/5] PYTHON RUNTIME DETECTION & ZERO-PREREQ PROVISIONING
rem ===========================================================================
echo %C_CYAN%[2/5] Python Runtime%C_RST%
set "PYTHON_CMD="
set "PYTHON_LOC="

if exist "!ROOT_DIR!\python_env\python.exe" (
    set PYTHON_CMD="!ROOT_DIR!\python_env\python.exe"
    set "PYTHON_LOC=Core Portable Environment (!ROOT_DIR!\python_env)"
    goto CHECK_PYTHON_VER
)
if exist "!ROOT_DIR!\venv\Scripts\python.exe" (
    set PYTHON_CMD="!ROOT_DIR!\venv\Scripts\python.exe"
    set "PYTHON_LOC=Core Virtual Environment (!ROOT_DIR!\venv)"
    goto CHECK_PYTHON_VER
)

rem --- No isolated Core Python found; check system Python ---
set "SYS_PY_CMD="
set "SYS_PY_VER="
py -3.11 --version >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "SYS_PY_CMD=py -3.11"
    for /f "tokens=2 delims= " %%V in ('py -3.11 --version 2^>^&1') do set "SYS_PY_VER=%%V"
) else (
    py -3 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "SYS_PY_CMD=py -3"
        for /f "tokens=2 delims= " %%V in ('py -3 --version 2^>^&1') do set "SYS_PY_VER=%%V"
    ) else (
        python --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "SYS_PY_CMD=python"
            for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set "SYS_PY_VER=%%V"
        )
    )
)

if "!UNATTENDED!"=="1" (
    echo %C_CYAN%[ .. ]%C_RST% No isolated Core Python found. Provisioning Portable Python 3.11.18 automatically...
    goto INSTALL_PYTHON
)

if not "!SYS_PY_CMD!"=="" goto OFFER_SYS_OR_PORTABLE
goto OFFER_PORTABLE_ONLY

:OFFER_SYS_OR_PORTABLE
echo %C_YELLOW%[WARN]%C_RST% No isolated Hecos Python found. System Python !SYS_PY_VER! detected (!SYS_PY_CMD!).
echo.
echo   An isolated Portable Python 3.11.18 (includes tkinter, pip, venv, C runtime)
echo   is strongly recommended so Hecos never conflicts with your system packages.
echo.
echo   %C_CYAN%1.%C_RST% Install Isolated Portable Python 3.11.18 %C_GREEN%(Recommended)%C_RST%
echo   %C_CYAN%2.%C_RST% Use System Python !SYS_PY_VER! (may miss binary wheels if not 3.11)
echo   %C_DIM%3. Exit%C_RST%
echo.
set "PY_CHOICE="
set /p PY_CHOICE="  %C_CYAN%>>%C_RST% Select option (1-3) [1]: "
if "!PY_CHOICE!"=="" set "PY_CHOICE=1"
if "!PY_CHOICE!"=="1" goto INSTALL_PYTHON
if "!PY_CHOICE!"=="2" (
    set "PYTHON_CMD=!SYS_PY_CMD!"
    set "PYTHON_LOC=Global System Python (!SYS_PY_CMD!)"
    goto CHECK_PYTHON_VER
)
exit /b 0

:OFFER_PORTABLE_ONLY
echo %C_YELLOW%[WARN]%C_RST% Python is NOT installed on this computer.
echo.
echo   Hecos can download and configure a self-contained Portable Python 3.11.18
echo   automatically (no manual installation or admin rights needed).
echo.
echo   %C_CYAN%1.%C_RST% Download ^& Install Portable Python 3.11.18 %C_GREEN%(Recommended)%C_RST%
echo   %C_DIM%2. Exit%C_RST%
echo.
set "PY_CHOICE="
set /p PY_CHOICE="  %C_CYAN%>>%C_RST% Select option (1-2) [1]: "
if "!PY_CHOICE!"=="" set "PY_CHOICE=1"
if "!PY_CHOICE!"=="1" goto INSTALL_PYTHON
exit /b 0

:CHECK_PYTHON_VER
echo %C_GREEN%[ OK ]%C_RST% Python found: !PYTHON_LOC!
set "PY_VER="
for /f "tokens=2 delims= " %%V in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VER=%%V"
echo        Version: %C_WHITE%!PY_VER!%C_RST%
echo [%DATE% %TIME%] Python selected: !PYTHON_LOC! ^(!PY_VER!^) >> "!SETUP_LOG!"

set "PY_MAJOR="
set "PY_MINOR="
for /f "tokens=1,2 delims=." %%A in ("!PY_VER!") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)

if not "!PY_MAJOR!"=="3" (
    echo %C_RED%[FAIL]%C_RST% Hecos requires Python 3.10+. Found: !PY_VER!
    if "!UNATTENDED!"=="0" pause
    exit /b 1
)

if !PY_MINOR! LSS 10 goto PYTHON_TOO_OLD
if not "!PY_MINOR!"=="11" goto PYTHON_NON_311
echo.
goto INSTALL_DEPS

:PYTHON_TOO_OLD
echo %C_RED%[FAIL]%C_RST% Hecos requires Python 3.10+. Found: !PY_VER!
if "!UNATTENDED!"=="1" goto INSTALL_PYTHON
echo.
echo   %C_CYAN%1.%C_RST% Download ^& Install Portable Python 3.11.18 %C_GREEN%(Recommended)%C_RST%
echo   %C_DIM%2. Exit%C_RST%
set "PY_UPG="
set /p PY_UPG="  %C_CYAN%>>%C_RST% Select option (1-2) [1]: "
if "!PY_UPG!"=="" set "PY_UPG=1"
if "!PY_UPG!"=="1" goto INSTALL_PYTHON
exit /b 1

:PYTHON_NON_311
echo %C_YELLOW%[WARN]%C_RST% Python !PY_VER! detected. Python 3.11.x is recommended for full wheel compatibility.
if "!UNATTENDED!"=="1" goto INSTALL_DEPS
echo   %C_CYAN%1.%C_RST% Continue with Python !PY_VER!
echo   %C_CYAN%2.%C_RST% Install Portable Python 3.11.18 instead %C_GREEN%(Recommended)%C_RST%
echo   %C_DIM%3. Exit%C_RST%
set "PY_ALT="
set /p PY_ALT="  %C_CYAN%>>%C_RST% Select option (1-3) [2]: "
if "!PY_ALT!"=="" set "PY_ALT=2"
if "!PY_ALT!"=="2" goto INSTALL_PYTHON
if "!PY_ALT!"=="3" exit /b 0
echo.
goto INSTALL_DEPS

rem ===========================================================================
rem PROVISION PORTABLE PYTHON 3.11.18 (python-build-standalone + embed fallback)
rem ===========================================================================
:INSTALL_PYTHON
echo.
echo %C_CYAN%------------------------------------------------------------------------------%C_RST%
echo   %C_MAG%PROVISIONING PORTABLE PYTHON 3.11.18%C_RST%
echo %C_CYAN%------------------------------------------------------------------------------%C_RST%
call :PROVISION_PYTHON "!ROOT_DIR!\python_env"
if !ERRORLEVEL! NEQ 0 (
    echo %C_RED%[FAIL]%C_RST% Could not install Portable Python. Check your internet connection and retry.
    echo [%DATE% %TIME%] FAIL Python provisioning failed >> "!SETUP_LOG!"
    if "!UNATTENDED!"=="0" pause
    exit /b 1
)
set PYTHON_CMD="!ROOT_DIR!\python_env\python.exe"
set "PYTHON_LOC=Core Portable Environment (!ROOT_DIR!\python_env)"
echo %C_GREEN%[ OK ]%C_RST% Portable Python ready at !ROOT_DIR!\python_env\python.exe
echo [%DATE% %TIME%] Portable Python installed at !ROOT_DIR!\python_env >> "!SETUP_LOG!"
echo.

rem ===========================================================================
rem [3/5] INSTALLING / VERIFYING CORE DEPENDENCIES (via tomllib in setup_env)
rem ===========================================================================
:INSTALL_DEPS
echo %C_CYAN%[3/5] Core Dependencies%C_RST%
cd /d "!ROOT_DIR!"

if /i "!LAUNCH_MODE!"=="doctor" goto REGISTER_INSTALL

echo %C_CYAN%[ .. ]%C_RST% Syncing Python packages from pyproject.toml ^(first run may take 2-5 min^)...
echo [%DATE% %TIME%] Running dependency sync >> "!SETUP_LOG!"

!PYTHON_CMD! "hecos\setup_wizard.py" --install-deps
set "DEPS_RC=!ERRORLEVEL!"
if !DEPS_RC! NEQ 0 (
    echo.
    echo %C_RED%[FAIL]%C_RST% Essential dependency installation failed ^(exit code !DEPS_RC!^).
    echo [%DATE% %TIME%] FAIL dependency sync rc=!DEPS_RC! >> "!SETUP_LOG!"
    if "!UNATTENDED!"=="0" pause
    exit /b 1
)
echo %C_GREEN%[ OK ]%C_RST% Core dependencies verified.
echo.

rem ===========================================================================
rem [4/5] SHARED INSTALL REGISTRY UPDATE
rem ===========================================================================
:REGISTER_INSTALL
echo %C_CYAN%[4/5] Install Registry%C_RST%
set "TRAY_FLAG="
if not "!TRAY_DIR!"=="" (
    set "HECOS_TRAY_DIR=!TRAY_DIR!"
    set TRAY_FLAG=--tray-dir "!TRAY_DIR!"
)
!PYTHON_CMD! -c "import sys; sys.path.insert(0, r'!ROOT_DIR!'); from hecos.setup.setup_env import register_installation; p=register_installation(); print('[ OK ] Registered in: ' + p)"
echo.

rem ===========================================================================
rem [5/5] LAUNCH SETUP INTERFACE
rem ===========================================================================
echo %C_CYAN%[5/5] Launching Setup Interface%C_RST%
cd /d "!ROOT_DIR!"

if not exist "!ROOT_DIR!\hecos\setup\main.py" (
    echo %C_RED%[FAIL]%C_RST% Core setup module missing: !ROOT_DIR!\hecos\setup\main.py
    if "!UNATTENDED!"=="0" pause
    exit /b 1
)

if /i "!LAUNCH_MODE!"=="install" (
    echo %C_CYAN%[ ^>^> ]%C_RST% Running unattended Core finalization ^(Piper TTS, fixes, autostart^)...
    !PYTHON_CMD! "hecos\setup_wizard.py" install --unattended --skip-deps !TRAY_FLAG!
    set "WIZ_RC=!ERRORLEVEL!"
) else if /i "!LAUNCH_MODE!"=="web" (
    echo %C_CYAN%[ ^>^> ]%C_RST% Launching Web Setup Wizard ^(localhost^)...
    !PYTHON_CMD! "hecos\setup_wizard.py" --web !TRAY_FLAG!
    set "WIZ_RC=!ERRORLEVEL!"
) else if /i "!LAUNCH_MODE!"=="doctor" (
    !PYTHON_CMD! "hecos\setup_wizard.py" doctor !TRAY_FLAG!
    set "WIZ_RC=!ERRORLEVEL!"
) else (
    echo %C_CYAN%[ ^>^> ]%C_RST% Launching Hecos Setup Wizard...
    !PYTHON_CMD! "hecos\setup_wizard.py" menu !TRAY_FLAG!
    set "WIZ_RC=!ERRORLEVEL!"
)

echo [%DATE% %TIME%] Setup wizard finished with code !WIZ_RC! >> "!SETUP_LOG!"

if !WIZ_RC! EQU 1 (
    echo.
    echo %C_RED%[FAIL]%C_RST% Setup Wizard exited with error code !WIZ_RC!. See output above or !SETUP_LOG!
    if "!UNATTENDED!"=="0" pause
)
exit /b !WIZ_RC!


rem ===========================================================================
rem SUBROUTINES
rem ===========================================================================

:PROVISION_PYTHON
set "TARGET_PY_DIR=%~1"
set "PBS_RELEASE=20261110"
set "PBS_ASSET=cpython-3.11.18+20261110-x86_64-pc-windows-msvc-install_only.tar.gz"
set "PBS_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.11.18%%2B20261110-x86_64-pc-windows-msvc-install_only.tar.gz"
set "PBS_SUMS_URL=https://github.com/astral-sh/python-build-standalone/releases/download/20261110/SHA256SUMS"
set "TMP_WORK=%TEMP%\hecos_py_setup_%RANDOM%"
set "TMP_TGZ=!TMP_WORK!\python_standalone.tar.gz"
set "TMP_SUMS=!TMP_WORK!\SHA256SUMS"

mkdir "!TMP_WORK!" >nul 2>&1

echo %C_CYAN%[ .. ]%C_RST% Downloading standalone Python 3.11.18 ^(~47 MB, includes tkinter ^& pip^)...
where curl.exe >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    curl.exe --fail -L --retry 3 --retry-delay 2 --progress-bar -o "!TMP_TGZ!" "!PBS_URL!"
) else (
    powershell -NoProfile -NonInteractive -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PBS_URL!' -OutFile '!TMP_TGZ!' -UseBasicParsing"
)

if !ERRORLEVEL! NEQ 0 goto PROVISION_FALLBACK_EMBED
if not exist "!TMP_TGZ!" goto PROVISION_FALLBACK_EMBED

rem --- Best-effort SHA256 verification ---
echo %C_CYAN%[ .. ]%C_RST% Verifying archive checksum...
set "SUMS_OK=0"
where curl.exe >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    curl.exe --fail -sSL --retry 2 -o "!TMP_SUMS!" "!PBS_SUMS_URL!" >nul 2>&1
    if !ERRORLEVEL! EQU 0 set "SUMS_OK=1"
)
if "!SUMS_OK!"=="1" (
    set "HASH_CHECK_FILE=!TMP_TGZ!"
    set "HASH_SUMS_FILE=!TMP_SUMS!"
    set "HASH_ASSET=!PBS_ASSET!"
    powershell -NoProfile -NonInteractive -Command "$line = Get-Content $env:HASH_SUMS_FILE | Where-Object { $_ -like ('*' + $env:HASH_ASSET) } | Select-Object -First 1; if (-not $line) { exit 2 }; $expected = ($line -split '\s+')[0].Trim().ToLower(); $actual = (Get-FileHash -Algorithm SHA256 $env:HASH_CHECK_FILE).Hash.ToLower(); if ($actual -eq $expected) { exit 0 } else { exit 1 }"
    set "HASH_RC=!ERRORLEVEL!"
    if !HASH_RC! EQU 0 (
        echo %C_GREEN%[ OK ]%C_RST% SHA256 checksum verified.
    ) else if !HASH_RC! EQU 1 (
        echo %C_RED%[FAIL]%C_RST% SHA256 checksum MISMATCH! Deleting corrupted download...
        rmdir /s /q "!TMP_WORK!" >nul 2>&1
        exit /b 1
    ) else (
        echo %C_YELLOW%[WARN]%C_RST% Asset hash entry not found; continuing anyway.
    )
) else (
    echo %C_YELLOW%[WARN]%C_RST% Could not fetch SHA256SUMS; skipping checksum verification.
)

echo %C_CYAN%[ .. ]%C_RST% Extracting Python into !TARGET_PY_DIR! ...
tar -xzf "!TMP_TGZ!" -C "!TMP_WORK!"
if !ERRORLEVEL! NEQ 0 goto PROVISION_FALLBACK_EMBED
if not exist "!TMP_WORK!\python\python.exe" goto PROVISION_FALLBACK_EMBED

if exist "!TARGET_PY_DIR!" rmdir /s /q "!TARGET_PY_DIR!" >nul 2>&1
mkdir "!TARGET_PY_DIR!" >nul 2>&1
robocopy "!TMP_WORK!\python" "!TARGET_PY_DIR!" /E /MOVE /NFL /NDL /NJH /NJS /NC /NS /NP >nul 2>&1
if not exist "!TARGET_PY_DIR!\python.exe" goto PROVISION_FALLBACK_EMBED

rmdir /s /q "!TMP_WORK!" >nul 2>&1
exit /b 0

:PROVISION_FALLBACK_EMBED
echo %C_YELLOW%[WARN]%C_RST% Standalone Python download/extract failed. Trying python.org 3.11.9 embeddable fallback...
rmdir /s /q "!TMP_WORK!" >nul 2>&1
mkdir "!TMP_WORK!" >nul 2>&1
set "EMBED_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "TMP_ZIP=!TMP_WORK!\python_embed.zip"

powershell -NoProfile -NonInteractive -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!EMBED_URL!' -OutFile '!TMP_ZIP!' -UseBasicParsing"
if !ERRORLEVEL! NEQ 0 (
    rmdir /s /q "!TMP_WORK!" >nul 2>&1
    exit /b 1
)

if exist "!TARGET_PY_DIR!" rmdir /s /q "!TARGET_PY_DIR!" >nul 2>&1
mkdir "!TARGET_PY_DIR!" >nul 2>&1
powershell -NoProfile -NonInteractive -Command "Expand-Archive -Path '!TMP_ZIP!' -DestinationPath '!TARGET_PY_DIR!' -Force"
if not exist "!TARGET_PY_DIR!\python.exe" (
    rmdir /s /q "!TMP_WORK!" >nul 2>&1
    exit /b 1
)

for %%F in ("!TARGET_PY_DIR!\*._pth") do (
    powershell -NoProfile -NonInteractive -Command "(Get-Content '%%~fF') -replace '#import site', 'import site' | Set-Content '%%~fF'"
)
powershell -NoProfile -NonInteractive -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '!TARGET_PY_DIR!\get-pip.py' -UseBasicParsing"
"!TARGET_PY_DIR!\python.exe" "!TARGET_PY_DIR!\get-pip.py" --quiet
set "PIP_RC=!ERRORLEVEL!"
rmdir /s /q "!TMP_WORK!" >nul 2>&1
if !PIP_RC! NEQ 0 exit /b 1
echo %C_YELLOW%[WARN]%C_RST% Installed embeddable Python fallback ^(note: tkinter is not included in embeddable builds^).
exit /b 0

:DETECT_TRAY
set "TRAY_DIR="
set "TRAY_WARN=0"
if not "!ARG_TRAY_DIR!"=="" (
    if exist "!ARG_TRAY_DIR!\tray\version" (
        set "TRAY_DIR=!ARG_TRAY_DIR!"
        exit /b 0
    )
)
if not "%HECOS_TRAY_DIR%"=="" (
    if exist "%HECOS_TRAY_DIR%\tray\version" (
        set "TRAY_DIR=%HECOS_TRAY_DIR%"
        exit /b 0
    )
)
set "REG_FILE=%LOCALAPPDATA%\Hecos\install.toml"
if exist "!REG_FILE!" (
    for /f "usebackq tokens=1,* delims==" %%K in ("!REG_FILE!") do (
        set "RK=%%~K"
        set "RV=%%~L"
        set "RK=!RK: =!"
        if /i "!RK!"=="tray_path" (
            set "RV=!RV:'=!"
            if "!RV:~0,1!"==" " set "RV=!RV:~1!"
            if exist "!RV!\tray\version" (
                set "TRAY_DIR=!RV!"
                exit /b 0
            )
        )
    )
)
for %%P in ("!ROOT_DIR!\..") do set "CORE_PARENT=%%~fP"
if "!CORE_PARENT:~-1!"=="\" set "CORE_PARENT=!CORE_PARENT:~0,-1!"
if exist "!CORE_PARENT!\Hecos-Tray\tray\version" (
    set "TRAY_DIR=!CORE_PARENT!\Hecos-Tray"
    exit /b 0
)
if exist "C:\Hecos-Tray\tray\version" (
    set "TRAY_DIR=C:\Hecos-Tray"
    exit /b 0
)
for /d %%D in ("!CORE_PARENT!\Hecos-Tray-*") do (
    if exist "%%D\tray\version" (
        if "!TRAY_DIR!"=="" (
            set "TRAY_DIR=%%D"
            set "TRAY_WARN=1"
        )
    )
)
if "!TRAY_DIR!"=="" (
    for /d %%D in ("C:\Hecos-Tray-*") do (
        if exist "%%D\tray\version" (
            if "!TRAY_DIR!"=="" (
                set "TRAY_DIR=%%D"
                set "TRAY_WARN=1"
            )
        )
    )
)
exit /b 0

:VALIDATE_PATH
set "CHECK_PATH=%~1"
set "PATH_STATUS=OK"
set "PATH_MSG=Safe path"
for /f "usebackq tokens=1,* delims==" %%S in (`powershell -NoProfile -NonInteractive -Command "$p=$env:CHECK_PATH; $e=@(); $w=@(); if($p -match '\s'){$e+='contains spaces'}; if($p -cmatch '[\u0080-\uFFFF]'){$e+='contains non-ASCII characters'}; $c=if($p.Length -ge 2 -and $p[1] -eq ':'){$p.Substring(2)}else{$p}; if($c -match '[\x21\x25\x5E\x26\x28\x29\x3D\x3B\x2C\x60\x22\x27]'){$e+='contains unsafe characters'}; if($p.Length -gt 80){$w+='path longer than 80 chars'}; if($p -imatch 'onedrive'){$w+='inside OneDrive'}; if($p -imatch 'program files|\\windows\\'){$w+='inside protected system folder'}; if($p -imatch '\\temp\\|\\tmp\\'){$w+='inside Temp folder'}; if($e.Count -gt 0){'ERR=' + ($e -join '; ')} elseif($w.Count -gt 0){'WARN=' + ($w -join '; ')} else {'OK=Safe path'}"`) do (
    set "PATH_STATUS=%%S"
    set "PATH_MSG=%%T"
)
exit /b 0
