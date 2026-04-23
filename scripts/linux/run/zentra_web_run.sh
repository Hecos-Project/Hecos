#!/bin/bash
# ZENTRA -- Native Web Server (Linux)

cd "$(dirname "$0")/../../.."
ROOT_DIR=$(pwd)

echo ""
echo " =============================================================="
echo "  ZENTRA NATIVE WEB INTERFACE"
echo " =============================================================="
echo ""

# 1. Search for Python
if [ -d "python_env" ]; then
    PYTHON_CMD="./python_env/bin/python"
elif [ -d "venv" ]; then
    PYTHON_CMD="./venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo " [*] Using Python: $PYTHON_CMD"
echo " [!] Starting control monitor in WEB mode..."
echo " [!] Opening browser automatically..."
echo ""

# Starting the monitor
$PYTHON_CMD zentra/monitor.py --script zentra.modules.web_ui.server

echo ""
echo " [!] Watchdog terminated."
sleep 5
