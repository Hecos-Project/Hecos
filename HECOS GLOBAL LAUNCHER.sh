#!/bin/bash
# Hecos Global Launcher for Linux

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR" || exit 1

show_menu() {
    clear
    echo "=============================================================================="
    echo "                             HECOS GLOBAL LAUNCHER"
    echo "=============================================================================="
    echo ""
    echo " 1. Install / Setup"
    echo " 2. Start Hecos (Web UI)"
    echo " 3. Start Hecos (Console)"
    echo " 4. Exit"
    echo ""
    echo " ------------------------------------------------------------------------------"
    echo " [INFO] All advanced scripts are located in the 'scripts' folder."
    echo " [TIP]  For the best experience, we recommend using the standalone"
    echo "        'Hecos Tray' application to install, manage, and update Hecos."
    echo " ------------------------------------------------------------------------------"
    echo ""
    read -p "Select an option (1-4): " choice

    case $choice in
        1)
            echo ""
            echo "[*] Starting Setup..."
            if [ -f "scripts/linux/setup/HECOS_SETUP_WIZARD.sh" ]; then
                bash "scripts/linux/setup/HECOS_SETUP_WIZARD.sh"
            else
                echo "[!] Setup script not found."
                read -p "Press Enter to continue..."
            fi
            show_menu
            ;;
        2)
            echo ""
            echo "[*] Starting Hecos Web UI..."
            if [ -f "scripts/linux/run/HECOS_WEBUI_RUN_LINUX.sh" ]; then
                bash "scripts/linux/run/HECOS_WEBUI_RUN_LINUX.sh"
            else
                echo "[!] Web run script not found."
                read -p "Press Enter to continue..."
                show_menu
            fi
            ;;
        3)
            echo ""
            echo "[*] Starting Hecos Console..."
            if [ -f "scripts/linux/run/HECOS_CONSOLE_RUN_LINUX.sh" ]; then
                bash "scripts/linux/run/HECOS_CONSOLE_RUN_LINUX.sh"
            else
                echo "[!] Console run script not found."
                read -p "Press Enter to continue..."
            fi
            show_menu
            ;;
        4)
            exit 0
            ;;
        *)
            show_menu
            ;;
    esac
}

show_menu
