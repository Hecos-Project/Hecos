@echo off
setlocal enabledelayedexpansion
title Hecos Global Launcher

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

rem --- Determine Core root directory dynamically ---
set "SCRIPT_DIR=%~dp0"
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"
cd /d "!SCRIPT_DIR!"

rem --- Safe Path Validation (custom locations allowed; only unsafe paths blocked) ---
call :VALIDATE_PATH "!SCRIPT_DIR!"
if /i "!PATH_STATUS!"=="ERR" (
    cls
    echo.
    echo %C_RED%==============================================================================%C_RST%
    echo %C_RED%  [FAIL] UNSAFE INSTALLATION PATH DETECTED%C_RST%
    echo %C_RED%==============================================================================%C_RST%
    echo.
    echo   Current location: %C_WHITE%!SCRIPT_DIR!%C_RST%
    echo   Problem:          %C_YELLOW%!PATH_MSG!%C_RST%
    echo.
    echo   Hecos can be installed on ANY drive or folder, as long as the path contains
    echo   no spaces, non-ASCII accents, or special shell characters.
    echo   Examples: %C_CYAN%C:\Hecos%C_RST%  or  %C_CYAN%D:\Apps\Hecos%C_RST%
    echo.
    echo   Run Setup Wizard ^(option 1^) or move the folder manually before continuing.
    echo.
    pause
)

:MENU
rem --- Read Core version ---
set "HECOS_VER=unknown"
if exist "hecos\core\version" set /p HECOS_VER=<"hecos\core\version"

rem --- Detect Python status for header ---
set "PY_STATUS=%C_YELLOW%Not configured (run Option 1)%C_RST%"
set "PYTHON_CMD="
if exist "!SCRIPT_DIR!\python_env\python.exe" (
    set PYTHON_CMD="!SCRIPT_DIR!\python_env\python.exe"
    set "PY_STATUS=%C_GREEN%Portable (python_env)%C_RST%"
) else if exist "!SCRIPT_DIR!\venv\Scripts\python.exe" (
    set PYTHON_CMD="!SCRIPT_DIR!\venv\Scripts\python.exe"
    set "PY_STATUS=%C_GREEN%Virtual Env (venv)%C_RST%"
) else (
    py -3 --version >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_CMD=py -3"
        set "PY_STATUS=%C_YELLOW%System (py -3)%C_RST%"
    ) else (
        python --version >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            set "PYTHON_CMD=python"
            set "PY_STATUS=%C_YELLOW%System (python)%C_RST%"
        )
    )
)

rem --- Detect Tray status ---
call :DETECT_TRAY
set "TRAY_STATUS=%C_DIM%Not detected (optional)%C_RST%"
if not "!TRAY_DIR!"=="" set "TRAY_STATUS=%C_GREEN%!TRAY_DIR!%C_RST%"

cls
echo.
echo %C_CYAN%==============================================================================%C_RST%
echo   %C_MAG%HECOS GLOBAL LAUNCHER%C_RST%   %C_CYAN%v!HECOS_VER!%C_RST%
echo %C_CYAN%==============================================================================%C_RST%
echo   %C_DIM%Core Path :%C_RST% %C_WHITE%!SCRIPT_DIR!%C_RST%
echo   %C_DIM%Python    :%C_RST% !PY_STATUS!
echo   %C_DIM%Hecos Tray:%C_RST% !TRAY_STATUS!
if /i "!PATH_STATUS!"=="WARN" (
    echo   %C_YELLOW%[WARN] Path advisory: !PATH_MSG!%C_RST%
)
echo %C_CYAN%------------------------------------------------------------------------------%C_RST%
echo.
echo   %C_CYAN%1.%C_RST% %C_WHITE%Install / Setup Wizard%C_RST%       %C_DIM%(Python, deps, Piper TTS, repair)%C_RST%
echo   %C_CYAN%2.%C_RST% %C_WHITE%Start Hecos (Web UI)%C_RST%         %C_DIM%(Native web server + watchdog)%C_RST%
echo   %C_CYAN%3.%C_RST% %C_WHITE%Start Hecos (Console)%C_RST%        %C_DIM%(Interactive text terminal)%C_RST%
echo   %C_CYAN%4.%C_RST% %C_WHITE%Start Coding Studio CLI%C_RST%      %C_DIM%(Interactive Aider ^& Dev Shell)%C_RST%
echo   %C_CYAN%5.%C_RST% %C_WHITE%System Diagnostics (Doctor)%C_RST%  %C_DIM%(Verify Python, deps, paths, Tray)%C_RST%
echo   %C_DIM%6. Exit%C_RST%
echo.
echo %C_DIM%------------------------------------------------------------------------------%C_RST%
echo   %C_DIM%[INFO] Advanced scripts live inside the 'scripts' folder.%C_RST%
echo   %C_DIM%[TIP]  Use "Hecos Tray" for one-click updates, dashboard, and background run.%C_RST%
echo %C_DIM%------------------------------------------------------------------------------%C_RST%
echo.
set "CH="
set /p CH="  %C_CYAN%>>%C_RST% Select an option (1-6): "

if "!CH!"=="1" goto SETUP
if "!CH!"=="2" goto START_WEB
if "!CH!"=="3" goto START_CONSOLE
if "!CH!"=="4" goto START_CODING_CLI
if "!CH!"=="5" goto DOCTOR
if "!CH!"=="6" exit /b 0

goto MENU

:SETUP
echo.
echo %C_CYAN%[ ^>^> ]%C_RST% Launching Setup Wizard...
if exist "scripts\windows\setup\HECOS_SETUP_WIZARD.bat" (
    call "scripts\windows\setup\HECOS_SETUP_WIZARD.bat"
) else (
    echo %C_RED%[FAIL]%C_RST% Setup script not found: scripts\windows\setup\HECOS_SETUP_WIZARD.bat
    pause
)
cd /d "!SCRIPT_DIR!"
goto MENU

:START_WEB
echo.
echo %C_CYAN%[ ^>^> ]%C_RST% Starting Hecos Web UI...
if exist "scripts\windows\run\HECOS_WEBUI_RUN_WIN.bat" (
    call "scripts\windows\run\HECOS_WEBUI_RUN_WIN.bat"
) else (
    echo %C_RED%[FAIL]%C_RST% Web run script not found.
    pause
)
cd /d "!SCRIPT_DIR!"
goto MENU

:START_CONSOLE
echo.
echo %C_CYAN%[ ^>^> ]%C_RST% Starting Hecos Console...
if exist "scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat" (
    call "scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat"
) else (
    echo %C_RED%[FAIL]%C_RST% Console run script not found.
    pause
)
cd /d "!SCRIPT_DIR!"
goto MENU

:START_CODING_CLI
echo.
echo %C_CYAN%[ ^>^> ]%C_RST% Starting Hecos Coding Studio CLI...
if exist "scripts\windows\run\HECOS_CODING_CLI_WIN.bat" (
    call "scripts\windows\run\HECOS_CODING_CLI_WIN.bat"
) else (
    echo %C_RED%[FAIL]%C_RST% Coding CLI script not found.
    pause
)
cd /d "!SCRIPT_DIR!"
goto MENU

:DOCTOR
echo.
if "!PYTHON_CMD!"=="" (
    echo %C_YELLOW%[WARN]%C_RST% Python is not installed yet. Run Option 1 ^(Setup Wizard^) first.
    echo.
    pause
    goto MENU
)
echo %C_CYAN%[ .. ]%C_RST% Running Hecos System Diagnostics...
echo.
!PYTHON_CMD! "hecos\setup_wizard.py" doctor
echo.
pause
goto MENU

:UNINSTALL
echo.
echo %C_CYAN%[ ^>^> ]%C_RST% Starting Uninstaller...
if not "!PYTHON_CMD!"=="" (
    !PYTHON_CMD! "hecos\setup_wizard.py" --uninstall
    pause
) else (
    echo %C_RED%[FAIL]%C_RST% Python not found; cannot launch uninstaller.
    pause
)
goto MENU

rem ===========================================================================
rem SUBROUTINES
rem ===========================================================================

:DETECT_TRAY
set "TRAY_DIR="
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
for %%P in ("!SCRIPT_DIR!\..") do set "PARENT_DIR=%%~fP"
if "!PARENT_DIR:~-1!"=="\" set "PARENT_DIR=!PARENT_DIR:~0,-1!"
if exist "!PARENT_DIR!\Hecos-Tray\tray\version" (
    set "TRAY_DIR=!PARENT_DIR!\Hecos-Tray"
    exit /b 0
)
if exist "C:\Hecos-Tray\tray\version" (
    set "TRAY_DIR=C:\Hecos-Tray"
    exit /b 0
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
