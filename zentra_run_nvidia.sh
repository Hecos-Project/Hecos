#!/bin/bash
# ZENTRA CORE - NVIDIA AI ACCELERATED RUNNER

# Spostati nella cartella in cui si trova questo script
cd "$(dirname "$0")"

VERSION=$(cat core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;33m==============================================================\033[0m"
echo -e "\033[1;33m ZENTRA CORE NVIDIA AI v${VERSION}\033[0m"
echo -e "\033[1;33m==============================================================\033[0m"
echo ""

# Avvia l'ambiente virtuale se esiste
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo -e "[*] Avvio sessione con supporto accelerazione CUDA..."
echo -e "[*] Premere \033[1;33mF9\033[0m per un Riavvio Sicuro del programma."
echo ""

python3 monitor.py

echo ""
echo "[!] Processo terminato."
echo "Premi INVIO per uscire..."
read
