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
else
    echo ""
    echo " +--------------------------------------------------+"
    echo " |                                                  |"
    echo " |     HECOS INSTALLATION COMPLETE!                 |"
    echo " |                                                  |"
    echo " +--------------------------------------------------+"
    echo ""
    echo " HOW TO START HECOS:"
    echo ""
    echo " 1. Look at your SYSTEM TRAY (usually top-right or"
    echo "    bottom-right corner of your screen)."
    echo ""
    echo " 2. RIGHT-CLICK the Hecos tray icon."
    echo ""
    echo " 3. Click [▶ Start Core] to launch the AI engine."
    echo ""
    echo " TIP: The tray icon will start automatically at"
    echo "      every login from now on."
    echo ""
    echo " If the icon does not appear, run:"
    echo " ./START_HECOS_TRAY_LINUX.sh"
    echo ""
    echo " You can close this terminal. Hecos runs in background."
    echo ""
    read -p "Press Enter to exit..."
fi
