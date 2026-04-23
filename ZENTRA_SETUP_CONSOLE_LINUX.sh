#!/bin/bash

echo ""
echo "======================================================="
echo "  STARTING ZENTRA SETUP WIZARD (CONSOLE)..."
echo "======================================================="
echo ""

# Go to the script directory
cd "$(dirname "$0")"

# Find python
PYTHON_CMD="python3"
if [ -f "venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
elif [ -f "python_env/bin/python" ]; then
    PYTHON_CMD="./python_env/bin/python"
fi

$PYTHON_CMD zentra/setup_wizard.py
