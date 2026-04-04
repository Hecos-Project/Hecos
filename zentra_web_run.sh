#!/bin/bash
# ZENTRA CORE - WEBUI WATCHDOG LAUNCHER

# Spostati nella root directory
cd "$(dirname "$0")"

VERSION=$(cat core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;32m==============================================================\033[0m"
echo -e "\033[1;32m  ZENTRA NATIVE WEB INTERFACE v${VERSION}\033[0m"
echo -e "\033[1;32m==============================================================\033[0m"
echo ""

# Attiva ambiente virtuale se esiste
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "[!] Avvio monitor di controllo in modalità WEB..."
echo "[!] Attendi il completamento pre-flight..."
echo ""

# Nota: Su Linux la gestione delle regole firewall non viene forzata
# automaticamente da questo script per prevenire root-access non necessari.
# Assicurati di avere la porta 7070 sbloccata nel tuo firewall (es. ufw allow 7070).

# Recupera l'IP della macchina per l'accesso remoto
LAN_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254', 1)); print(s.getsockname()[0])" 2>/dev/null)
if [ -z "$LAN_IP" ]; then
    LAN_IP="localhost"
fi

# Recupera lo schema HTTP/HTTPS da system.yaml
SCHEME=$(python3 -c "import yaml; print('https' if yaml.safe_load(open('config/system.yaml')).get('plugins',{}).get('WEB_UI',{}).get('https_enabled',False) else 'http')" 2>/dev/null)
if [ -z "$SCHEME" ]; then
    SCHEME="http"
fi

echo -e "\033[1;36m==============================================================\033[0m"
echo -e " \033[1;33m[ ACCESSO RAPIDO ]\033[0m"
echo -e " Se chiudi il browser per sbaglio o vuoi collegarti"
echo -e " dal telefono o tablet, usa l'indirizzo della tua rete:"
echo ""
echo -e " * Chat:     \033[4;34m${SCHEME}://${LAN_IP}:7070/chat\033[0m"
echo -e " * Config:   \033[4;34m${SCHEME}://${LAN_IP}:7070/zentra/config/ui\033[0m"
echo -e " * Drive:    \033[4;34m${SCHEME}://${LAN_IP}:7070/drive\033[0m"
echo -e "\033[1;36m==============================================================\033[0m"
echo ""

# Avviamo il monitor passando il modulo del server web standalone.
python3 monitor.py --script plugins.web_ui.server

echo ""
echo "[!] Watchdog terminato."
sleep 5
