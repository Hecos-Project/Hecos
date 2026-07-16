#!/bin/bash
# Hecos - Restart Tray Icon

# Navigate to the script's directory
cd "$(dirname "$0")"

echo ""
echo " [*] Restoring system tray icon..."
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

# Run the tray app in background (quietly)
nohup $PY_CMD -m hecos.tray.tray_app >/dev/null 2>&1 &

echo " [+] Command sent. The icon will appear shortly."
echo ""
sleep 1
exit 0
