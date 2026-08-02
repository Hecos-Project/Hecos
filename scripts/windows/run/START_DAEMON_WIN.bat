@echo off
title Hecos Supervisor (Daemon Mode)

:: Navigate to the project root (3 levels up from scripts/windows/run/)
cd /d "%~dp0\..\..\.."
call hecos_sdk\Scripts\activate.bat

echo ==================================================
echo  Starting Hecos Supervisor in Daemon Mode...
echo  If Hecos crashes, it will be restarted automatically.
echo  Close this window to stop everything.
echo ==================================================

python -m hecos.core.daemon

pause
