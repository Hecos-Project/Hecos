@echo off
setlocal
title Hecos Universal Launcher
color 0B

:MENU
cls
echo ==============================================================================
echo                              HECOS CORE LAUNCHER
echo ==============================================================================
echo.
echo  1. Start Hecos (Web UI)
echo  2. Start Hecos (Console)
echo  3. Install / Setup
echo  4. Uninstall
echo  5. Exit
echo.
echo  ------------------------------------------------------------------------------
echo  [INFO] All advanced scripts are located in the 'scripts' folder.
echo  [TIP]  For the best experience, we recommend using the standalone
echo         "Hecos Tray" application to install, manage, and update Hecos.
echo  ------------------------------------------------------------------------------
echo.
set /p CH="Select an option (1-5): "

if "%CH%"=="1" goto START_WEB
if "%CH%"=="2" goto START_CONSOLE
if "%CH%"=="3" goto SETUP
if "%CH%"=="4" goto UNINSTALL
if "%CH%"=="5" exit

goto MENU

:START_WEB
echo.
echo [*] Starting Hecos Web UI...
if exist "scripts\windows\run\HECOS_WEB_RUN_WIN.bat" (
    call "scripts\windows\run\HECOS_WEB_RUN_WIN.bat"
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
if exist "scripts\windows\setup\INSTALL_HECOS_WIN.bat" (
    call "scripts\windows\setup\INSTALL_HECOS_WIN.bat"
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
