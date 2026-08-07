@echo off
setlocal
title Hecos Global Launcher
color 0B

:MENU
cls
echo ==============================================================================
echo                             HECOS GLOBAL LAUNCHER
echo ==============================================================================
echo.
echo  1. Install / Setup
echo  2. Start Hecos (Web UI)
echo  3. Start Hecos (Console)
echo  4. Exit
echo.
echo  ------------------------------------------------------------------------------
echo  [INFO] All advanced scripts are located in the 'scripts' folder.
echo  [TIP]  For the best experience, we recommend using the standalone
echo         "Hecos Tray" application to install, manage, and update Hecos.
echo  ------------------------------------------------------------------------------
echo.
set /p CH="Select an option (1-4): "

if "%CH%"=="1" goto SETUP
if "%CH%"=="2" goto START_WEB
if "%CH%"=="3" goto START_CONSOLE
if "%CH%"=="4" exit

goto MENU

:START_WEB
echo.
echo [*] Starting Hecos Web UI...
if exist "scripts\windows\run\HECOS_WEBUI_RUN_WIN.bat" (
    call "scripts\windows\run\HECOS_WEBUI_RUN_WIN.bat"
) else (
    echo [!] Web run script not found.
    pause
)
exit

:START_CONSOLE
echo.
echo [*] Starting Hecos Console...
if exist "scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat" (
    call "scripts\windows\run\HECOS_CONSOLE_RUN_WIN.bat"
) else (
    echo [!] Console run script not found.
    pause
)
goto MENU

:SETUP
echo.
echo [*] Starting Setup...
if exist "scripts\windows\setup\HECOS_SETUP_WIZARD.bat" (
    call "scripts\windows\setup\HECOS_SETUP_WIZARD.bat"
) else (
    echo [!] Setup script not found.
    pause
)
goto MENU

:UNINSTALL
echo.
echo [*] Starting Uninstaller...
if exist "scripts\windows\setup\UNINSTALL_HECOS_WIN.bat" (
    call "scripts\windows\setup\UNINSTALL_HECOS_WIN.bat"
) else (
    echo [!] Uninstaller script not found.
    pause
)
goto MENU
