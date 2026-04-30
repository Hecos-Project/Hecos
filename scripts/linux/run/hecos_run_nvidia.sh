#!/bin/bash
# HECOS CORE - NVIDIA AI ACCELERATED RUNNER

# Spostati nella cartella root del progetto
cd "$(dirname "$0")/../../.."

VERSION=$(cat hecos/core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;33m==============================================================\033[0m"
echo -e "\033[1;33m HECOS CORE NVIDIA AI v${VERSION}\033[0m"
echo -e "\033[1;33m==============================================================\033[0m"
echo ""

# Avvia l'ambiente virtuale se esiste
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo -e "[*] Avvio sessione con supporto accelerazione CUDA..."
echo -e "[*] Premere \033[1;33mF9\033[0m per un Riavvio Sicuro del programma."
echo ""

python3 hecos/monitor.py

echo ""
echo "[!] Processo terminato."
echo "Premi INVIO per uscire..."
read
