#!/bin/bash
# ZENTRA CORE - WEBUI WATCHDOG LAUNCHER

# Spostati nella root directory
cd "$(dirname "$0")"

VERSION=$(cat zentra/core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;32m==============================================================\033[0m"
echo -e "\033[1;32m  ZENTRA NATIVE WEB INTERFACE v${VERSION}\033[0m"
echo -e "\033[1;32m==============================================================\033[0m"
echo ""

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "[!] Starting control monitor in WEB mode..."
echo "[!] Waiting for pre-flight completion..."
echo ""

# Note: On Linux, firewall rule management is not forced
# automatically by this script to prevent unnecessary root-access.
# Ensure you have port 7070 open in your firewall (e.g. ufw allow 7070).

# Recupera l'IP della macchina per l'accesso remoto
LAN_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254', 1)); print(s.getsockname()[0])" 2>/dev/null)
if [ -z "$LAN_IP" ]; then
    LAN_IP="localhost"
fi

# Recupera lo schema HTTP/HTTPS da system.yaml
SCHEME=$(python3 -c "import yaml; print('https' if yaml.safe_load(open('zentra/config/data/system.yaml')).get('plugins',{}).get('WEB_UI',{}).get('https_enabled',False) else 'http')" 2>/dev/null)
if [ -z "$SCHEME" ]; then
    SCHEME="http"
fi

echo -e "\033[1;36m==============================================================\033[0m"
echo -e " \033[1;33m[ QUICK ACCESS ]\033[0m"
echo -e " If you accidentally close the browser or want to"
echo -e " connect from your phone or tablet, use your network address:"
echo ""
echo -e " * Chat:     \033[4;34m${SCHEME}://${LAN_IP}:7070/chat\033[0m"
echo -e " * Config:   \033[4;34m${SCHEME}://${LAN_IP}:7070/zentra/config/ui\033[0m"
echo -e " * Drive:    \033[4;34m${SCHEME}://${LAN_IP}:7070/drive\033[0m"
echo -e "\033[1;36m==============================================================\033[0m"
echo ""

# Starting the monitor passing the standalone web server module.
python3 zentra/monitor.py --script zentra.modules.web_ui.server

echo ""
echo "[!] Watchdog terminated."
sleep 5
