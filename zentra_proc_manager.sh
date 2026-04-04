#!/bin/bash
# ZENTRA PROCESS MANAGER

# Spostati nella cartella in cui si trova questo script
cd "$(dirname "$0")"

VERSION=$(cat core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;35m==============================================================\033[0m"
echo -e "\033[1;35m ZENTRA PROCESS MANAGER v${VERSION}\033[0m"
echo -e "\033[1;35m==============================================================\033[0m"
echo ""

# Avvia l'ambiente virtuale se esiste
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo -e "[*] Avvio monitor di controllo processi (standalone)..."
echo ""

python3 zentra_proc_manager.py

echo ""
echo "[!] Processo terminato."
echo "Premi INVIO per uscire..."
read
