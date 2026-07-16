#!/bin/bash

# Navigate to the script's directory
cd "$(dirname "$0")"

echo "====================================================================="
echo "   HECOS SYSTEM UNINSTALLER"
echo "====================================================================="
echo ""
echo "Starting Hecos Setup Wizard..."
echo "Please use the Web Interface to proceed with uninstallation."
echo ""

# Detect Python
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    PY_CMD="venv/bin/python"
elif [ -d "python_env" ] && [ -f "python_env/bin/python" ]; then
    PY_CMD="python_env/bin/python"
elif command -v python3 &>/dev/null; then
    PY_CMD="python3"
else
    PY_CMD="python"
fi

$PY_CMD hecos/setup/main.py --uninstall --web

read -p "Press Enter to exit..."
