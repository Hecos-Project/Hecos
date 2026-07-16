#!/bin/bash

echo ""
echo "======================================================="
echo "  STARTING HECOS SETUP WIZARD (CONSOLE)..."
echo "======================================================="
echo ""

# Go to the script directory
cd "$(dirname "$0")/../../.."

# Find python
PYTHON_CMD="python3"
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    PYTHON_CMD="venv/bin/python"
elif [ -d "python_env" ] && [ -f "python_env/bin/python" ]; then
    PYTHON_CMD="python_env/bin/python"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

$PYTHON_CMD hecos/setup/main.py
