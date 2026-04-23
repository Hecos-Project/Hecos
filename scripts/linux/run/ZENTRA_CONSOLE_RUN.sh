#!/bin/bash
# ZENTRA CORE - ACTIVE SESSION RUNNER (Native Text Console)

# Spostati nella cartella principale del progetto
cd "$(dirname "$0")/../../.."
ROOT_DIR=$(pwd)

VERSION=$(cat zentra/core/version 2>/dev/null || echo "Unknown")

echo -e "\033[1;36m==============================================================\033[0m"
echo -e "\033[1;36m ZENTRA CORE NATIVE TERMINAL v${VERSION}\033[0m"
echo -e "\033[1;36m==============================================================\033[0m"
echo ""

# Start the portable environment if it exists
if [ -f "python_env/bin/activate" ]; then
    source python_env/bin/activate
elif [ -f "venv/bin/activate" ]; then
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
