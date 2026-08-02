@echo off
title Hecos Supervisor (Daemon Mode)

cd /d "%~dp0"
call hecos_sdk\Scripts\activate.bat

echo Starting Hecos Supervisor in Daemon Mode...
echo If Hecos crashes, it will be restarted automatically.
echo Close this window to stop everything.

python hecos_daemon.py

pause
