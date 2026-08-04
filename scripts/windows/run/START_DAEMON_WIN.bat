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

:: Generate and get the path to the named executable
for /f "delims=" %%i in ('python -c "import sys, os; sys.path.insert(0, os.getcwd()); from hecos.core.system.process_naming import get_named_executable; print(get_named_executable('hecos_daemon'))"') do set "HECOS_DAEMON_EXE=%%i"

"%HECOS_DAEMON_EXE%" -m hecos.core.daemon

pause
