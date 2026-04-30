#!/bin/bash
# HECOS PROCESS MANAGER

# Spostati nella cartella root del progetto
cd "$(dirname "$0")/../../.."

VERSION=$(cat hecos/core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;35m==============================================================\033[0m"
echo -e "\033[1;35m HECOS PROCESS MANAGER v${VERSION}\033[0m"
echo -e "\033[1;35m==============================================================\033[0m"
echo ""

# Start the virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo -e "[*] Starting standalone process monitor..."
echo ""

python3 scripts/utils/hecos_proc_manager.py

echo ""
echo "[!] Process terminated."
echo "Press ENTER to exit..."
read
