#!/bin/bash
cd "$(dirname "$0")/../../.."

if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
elif [ -d "python_env" ] && [ -f "python_env/bin/python" ]; then
    PYTHON_CMD="python_env/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

$PYTHON_CMD -m hecos.app.standalone_config_editor
read -p "Press Enter to exit..."
