#!/bin/bash
# START_DAEMON_LINUX.sh
# Hecos Supervisor (Daemon Mode) - Linux/macOS
# If Hecos crashes, it will be restarted automatically.
# Close this terminal to stop everything.

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

echo "=================================================="
echo " Starting Hecos Supervisor in Daemon Mode..."
echo " If Hecos crashes, it will be restarted automatically."
echo " Close this window to stop everything."
echo "=================================================="

$PYTHON_CMD -m hecos.core.daemon
