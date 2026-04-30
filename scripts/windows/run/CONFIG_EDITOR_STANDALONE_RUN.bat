@echo off
pushd "%~dp0"
cd ..\..\..
set ROOT_DIR=%CD%
popd
cd /d "%ROOT_DIR%"

start "HECOS Config Editor" cmd /c "python -c \"from hecos.ui.config_editor.core import ConfigEditor; ConfigEditor().run()\" && pause"
echo Editor started in a new window!
timeout /t 2 /nobreak >nul