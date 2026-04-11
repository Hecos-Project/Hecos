#!/bin/bash
# ZENTRA CORE - ACTIVE SESSION RUNNER (Native Text Console)

# Spostati nella cartella in cui si trova questo script
cd "$(dirname "$0")"

VERSION=$(cat zentra/core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;36m==============================================================\033[0m"
echo -e "\033[1;36m ZENTRA CORE NATIVE TERMINAL v${VERSION}\033[0m"
echo -e "\033[1;36m==============================================================\033[0m"
echo ""

# Start the virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo -e "[*] Starting interactive terminal..."
echo -e "[*] Press \033[1;33mF9\033[0m for a Safe Restart of the program."
echo ""

python3 zentra/monitor.py

echo ""
echo "[!] Process terminated."
echo "Press ENTER to exit..."
read
