#!/bin/bash
# Hecos - Restart Tray Icon

echo ""
echo " [*] Restoring system tray icon..."
echo ""

# Detect Python
if [ -d "venv" ]; then
    PY_CMD="./venv/bin/python"
elif [ -d "python_env" ]; then
    PY_CMD="./python_env/bin/python"
else
    PY_CMD="python3"
fi

# Run the tray app in background (quietly)
nohup $PY_CMD -m hecos.tray.tray_app >/dev/null 2>&1 &

echo " [+] Command sent. The icon will appear shortly."
echo ""
sleep 1
exit 0
