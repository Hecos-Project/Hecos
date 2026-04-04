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

echo -e "\033[1;36m==============================================================\033[0m"
echo -e "\033[1;36m 💡 ACCESSO RAPIDO\033[0m"
echo -e "\033[1;36m Se usi un terminale moderno, puoi usare Ctrl+Clic sui link:\033[0m"
echo ""
echo -e " \033[1;37m🌐 Chat:     http://localhost:7070/chat\033[0m"
echo -e " \033[1;37m⚙️ Config:   http://localhost:7070/zentra/config/ui\033[0m"
echo -e " \033[1;37m🗂️ Drive:    http://localhost:7070/drive\033[0m"
echo -e "\033[1;36m==============================================================\033[0m"
echo ""

# Avviamo il monitor passando il modulo del server web standalone.
python3 monitor.py --script plugins.web_ui.server

echo ""
echo "[!] Watchdog terminato."
sleep 5
