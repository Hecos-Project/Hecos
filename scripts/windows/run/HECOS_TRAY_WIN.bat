@echo off
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%\..\..\.."

@REM Generate the named executable for the Tray App
for /f "delims=" %%i in ('pythonw -c "import sys, os; sys.path.insert(0, os.getcwd()); from hecos.core.system.process_naming import get_named_executable; print(get_named_executable('hecos_tray', sys.executable))"') do set "HECOS_TRAY_EXE=%%i"

@REM Starts the Hecos System Tray Orchestrator quietly
start "" /b "%HECOS_TRAY_EXE%" -m hecos.tray.tray_app
