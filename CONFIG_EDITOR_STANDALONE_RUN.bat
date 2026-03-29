@echo off
start "ZENTRA Config Editor" cmd /c "cd /d %~dp0 && python config_tool.py && pause"
echo Editor avviato in una nuova finestra!
timeout /t 2 /nobreak >nul