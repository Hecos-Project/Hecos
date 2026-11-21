@echo off
setlocal enabledelayedexpansion
call "%~dp0ENABLE_TRAY_AUTOSTART.bat" %*
exit /b !ERRORLEVEL!
