#!/bin/bash
# HECOS CORE - Configuration UI Launcher

echo "==================================================="
echo "        HECOS CORE: CONTROL PANEL"
echo "==================================================="
echo ""
echo "[SYSTEM] Opening configuration interface..."
echo "[PATH] http://127.0.0.1:7070/hecos/config/ui"
echo ""

# Apertura automatica del browser a seconda del sistema
if which xdg-open > /dev/null
then
  xdg-open http://127.0.0.1:7070/hecos/config/ui
elif which gnome-open > /dev/null
then
  gnome-open http://127.0.0.1:7070/hecos/config/ui
elif which open > /dev/null
then
  open http://127.0.0.1:7070/hecos/config/ui
else
  echo "[ERROR] Unable to automatically open the browser on this OS."
  echo "Open manually: http://127.0.0.1:7070/hecos/config/ui"
  echo "Ensure Hecos WebUI is running."
fi

sleep 3
exit 0
