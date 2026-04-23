@echo off
start "ZENTRA Config Editor" cmd /c "cd /d %~dp0.. && python -c \"from zentra.ui.config_editor.core import ConfigEditor; ConfigEditor().run()\" && pause"
echo Editor started in a new window!
timeout /t 2 /nobreak >nul