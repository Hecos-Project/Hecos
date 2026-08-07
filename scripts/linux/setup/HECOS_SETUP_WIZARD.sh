#!/bin/bash

# Determine the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Determine ROOT directory dynamically
ROOT_DIR="$SCRIPT_DIR"
TRAY_DIR=""

if [ -f "$SCRIPT_DIR/../../../hecos/core/version" ]; then
    # Running from C:\Hecos\scripts\linux\setup\
    ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    TRAY_DIR="${ROOT_DIR}-Tray"
elif [ -f "$SCRIPT_DIR/../Hecos/hecos/core/version" ]; then
    # Running from C:\Hecos-Tray\
    ROOT_DIR="$(cd "$SCRIPT_DIR/../Hecos" && pwd)"
    TRAY_DIR="$(cd "$SCRIPT_DIR" && pwd)"
else
    # Fallback assuming we are in Hecos or Hecos-Tray
    if [[ "$SCRIPT_DIR" == *"-Tray" ]]; then
        ROOT_DIR="${SCRIPT_DIR%-Tray}"
        TRAY_DIR="$SCRIPT_DIR"
    else
        ROOT_DIR="$SCRIPT_DIR"
        TRAY_DIR="${ROOT_DIR}-Tray"
    fi
fi

# Switch to ROOT_DIR
cd "$ROOT_DIR" || exit 1

echo "=============================================================================="
echo "                         HECOS SETUP WIZARD (LINUX)"
echo "=============================================================================="
echo ""

# 1. Check Folders
echo "[SYSTEM CHECK]"
if [ -f "$ROOT_DIR/hecos/core/version" ]; then
    echo "[OK] Core found at: $ROOT_DIR"
else
    echo "[!] Core NOT found at: $ROOT_DIR"
fi

if [ -f "$TRAY_DIR/tray/version" ]; then
    echo "[OK] Tray found at: $TRAY_DIR"
else
    echo "[!] Tray NOT found at: $TRAY_DIR"
fi
echo ""

# 2. Python Detection
echo "[PYTHON DETECTION]"
PYTHON_CMD=""
PYTHON_LOC=""

if [ -f "$ROOT_DIR/venv/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
    PYTHON_LOC="Virtual Environment ($ROOT_DIR/venv)"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_LOC="Global System Path"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_LOC="Global System Path"
fi

if [ -n "$PYTHON_CMD" ]; then
    echo "[OK] Python found: $PYTHON_LOC"
    $PYTHON_CMD --version
    echo ""
    
    # Check if venv exists, if not ask to create it
    if [ "$PYTHON_LOC" == "Global System Path" ] && [ ! -d "$ROOT_DIR/venv" ]; then
        echo "[!] Python is installed globally, but Hecos Virtual Environment is missing."
        echo ""
        echo " It is highly recommended to install Hecos inside a Virtual Environment (venv)."
        echo " Do you want to create it now and install dependencies?"
        echo ""
        echo "  1. Create Virtual Environment (Recommended)"
        echo "  2. Skip and run with Global Python (Not Recommended)"
        echo "  3. Exit"
        echo ""
        read -p "Select an option (1-3): " CH
        
        if [ "$CH" == "1" ]; then
            CREATE_VENV=1
        elif [ "$CH" == "2" ]; then
            echo "[*] Proceeding with global python..."
            sleep 2
        else
            exit 0
        fi
    else
        echo "[*] Python environment is ready. Proceeding to Setup..."
        sleep 2
    fi
else
    echo "[!] Python 3 is NOT installed or not found."
    echo ""
    echo " In order to run Hecos Core or the Setup Wizard, you need Python 3."
    echo " Please install it using your system package manager (e.g. sudo apt install python3 python3-venv)"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

if [ "$CREATE_VENV" == "1" ]; then
    echo ""
    echo "=============================================================================="
    echo "                CREATING VIRTUAL ENVIRONMENT & INSTALLING DEPS"
    echo "=============================================================================="
    
    echo "[*] Creating venv in $ROOT_DIR/venv..."
    $PYTHON_CMD -m venv "$ROOT_DIR/venv"
    
    if [ $? -ne 0 ]; then
        echo "[-] Failed to create venv. You might need to install python3-venv:"
        echo "    sudo apt install python3-venv"
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
    
    echo "[*] Upgrading PIP..."
    $PYTHON_CMD -m pip install --upgrade pip
    
    echo "[*] Installing Hecos dependencies..."
    if [ -f "$ROOT_DIR/requirements.txt" ]; then
        $PYTHON_CMD -m pip install -r "$ROOT_DIR/requirements.txt"
    else
        echo "[!] requirements.txt not found! Skipping dependencies."
    fi
    
    echo ""
    echo "[SUCCESS] Virtual Environment Created and Dependencies Installed!"
    sleep 2
fi

echo ""
echo "=============================================================================="
echo "                          STARTING INTERFACE"
echo "=============================================================================="
if [ -f "$ROOT_DIR/hecos/setup_wizard.py" ]; then
    echo "[*] Launching Core Setup Wizard..."
    cd "$ROOT_DIR" || exit 1
    $PYTHON_CMD "hecos/setup_wizard.py"
elif [ -f "$TRAY_DIR/START_HECOS_TRAY_LINUX.sh" ]; then
    echo "[!] Core Setup Wizard not found (Core is not downloaded yet)."
    echo "[*] Launching Hecos Tray instead. You can download the Core from there."
    sleep 3
    bash "$TRAY_DIR/START_HECOS_TRAY_LINUX.sh"
else
    echo "[!] CRITICAL ERROR: Neither Core nor Tray were found!"
    read -p "Press Enter to exit..."
fi
