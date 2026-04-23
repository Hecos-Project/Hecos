#!/bin/bash
# Zentra Core - Restart Tray Icon

echo ""
echo " [*] Ripristino icona della barra delle applicazioni (Tray Icon)..."
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
nohup $PY_CMD -m zentra.tray.tray_app >/dev/null 2>&1 &

echo " [+] Comando inviato. L'icona apparira' a breve."
echo ""
sleep 1
exit 0
