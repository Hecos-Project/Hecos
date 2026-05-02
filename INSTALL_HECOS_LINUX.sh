#!/bin/bash

echo ""
echo " +--------------------------------------------------+"
echo " |                                                  |"
echo " |          HECOS CORE - INITIAL BOOTSTRAP         |"
echo " |                                                  |"
echo " +--------------------------------------------------+"
echo ""

# 1. Search for Python
echo " [*] Detecting Python..."
PY_CMD=""

if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
fi

# 2. Missing Python Logic
if [ -z "$PY_CMD" ]; then
    echo ""
    echo " [!] OH NO! PYTHON NOT FOUND."
    echo ""
    echo " Hecos requires Python 3.10 or higher."
    echo ""
    echo " HOW TO FIX THIS:"
    echo " - Ubuntu/Debian: sudo apt update && sudo apt install python3"
    echo " - macOS: brew install python"
    echo " - Others: Visit https://www.python.org/downloads/"
    echo ""
    read -p "[*] Press Enter to exit..."
    exit 1
fi

# 3. Launch Setup Wizard
echo " [+] Python detected: $PY_CMD"
echo " [*] Launching Hecos Setup Wizard..."
echo ""

$PY_CMD hecos/setup_wizard.py --web

if [ $? -ne 0 ]; then
    echo ""
    echo " [-] Setup Wizard ended with errors."
    read -p "Press Enter to exit..."
fi
