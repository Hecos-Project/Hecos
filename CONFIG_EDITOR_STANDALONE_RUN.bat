@echo off
start "ZENTRA Config Editor" cmd /c "cd /d %~dp0 && python config_tool.py && pause"
echo Editor started in a new window!
timeout /t 2 /nobreak >nul