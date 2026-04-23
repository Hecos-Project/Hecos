#!/bin/bash
# Zentra Core - Linux Library Installer

cd "$(dirname "$0")/../../.."
ROOT_DIR=$(pwd)

echo ""
echo " +--------------------------------------------------+"
echo " |                                                  |"
echo " |      ZENTRA CORE - LINUX LIBRARY INSTALLER       |"
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

if [ -z "$PY_CMD" ]; then
    echo " [-] Python not found. Please install Python 3.10+."
    exit 1
fi

# 2. Create VENV
if [ ! -d "venv" ]; then
    echo " [*] Creating virtual environment..."
    $PY_CMD -m venv venv
fi

# 3. Install Dependencies
echo " [*] Installing requirements..."
./venv/bin/pip install -r requirements.txt

# 4. Success
echo ""
echo " [+] Installation complete!"
echo " [*] To start Zentra, use: bash scripts/linux/run/zentra_web_run.sh"
echo ""
