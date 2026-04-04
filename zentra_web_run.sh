#!/bin/bash
# ZENTRA CORE - WEBUI WATCHDOG LAUNCHER

# Spostati nella root directory
cd "$(dirname "$0")"

VERSION=$(cat core/version 2>/dev/null || echo "Unknown")

echo "======================================"
echo -e "\033[1;32m ZENTRA NATIVE WEB INTERFACE v${VERSION}\033[0m"
echo "======================================"
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

# Avviamo il monitor passando il modulo del server web standalone.
python3 monitor.py --script plugins.web_ui.server

echo ""
echo "[!] Watchdog terminato."
sleep 5
