#!/bin/bash
# ZENTRA Config Editor (Standalone Logger)

cd "$(dirname "$0")"

echo "Avvio Editor di configurazione..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 config_tool.py

echo "Editor terminato. Premi INVIO per uscire..."
read
