#!/bin/bash
# ZENTRA CORE - ACTIVE SESSION RUNNER (Native Text Console)

# Sposati nella cartella in cui si trova questo script
cd "$(dirname "$0")"

echo "==================================================="
echo " ZENTRA CORE - CONOSOLE NATIVA ATTIVA "
echo "==================================================="

# Avvia l'ambiente virtuale se esiste
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 monitor.py

echo "Premi INVIO per uscire..."
read
