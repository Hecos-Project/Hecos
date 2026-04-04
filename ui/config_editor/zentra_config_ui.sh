#!/bin/bash
# ZENTRA CORE - Configuration UI Launcher

echo "==================================================="
echo "        ZENTRA CORE: PANNELLO DI CONTROLLO"
echo "==================================================="
echo ""
echo "[SISTEMA] Apertura interfaccia di configurazione..."
echo "[PATH] http://127.0.0.1:7070/zentra/config/ui"
echo ""

# Apertura automatica del browser a seconda del sistema
if which xdg-open > /dev/null
then
  xdg-open http://127.0.0.1:7070/zentra/config/ui
elif which gnome-open > /dev/null
then
  gnome-open http://127.0.0.1:7070/zentra/config/ui
elif which open > /dev/null
then
  open http://127.0.0.1:7070/zentra/config/ui
else
  echo "[ERRORE] Impossibile aprire automaticamente il browser su questo SO."
  echo "Apri manualmente: http://127.0.0.1:7070/zentra/config/ui"
  echo "Assicurati che Zentra WebUI sia attiva."
fi

sleep 3
exit 0
