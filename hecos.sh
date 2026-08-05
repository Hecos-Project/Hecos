#!/bin/bash

# Hecos Universal Launcher for Linux

cd "$(dirname "$0")"

show_menu() {
    clear
    echo "=============================================================================="
    echo "                              HECOS CORE LAUNCHER"
    echo "=============================================================================="
    echo ""
    echo "  1. Start Hecos (Web UI)"
    echo "  2. Start Hecos (Console)"
    echo "  3. Install / Setup"
    echo "  4. Uninstall"
    echo "  5. Exit"
    echo ""
    echo "  ------------------------------------------------------------------------------"
    echo "  [INFO] All advanced scripts are located in the 'scripts' folder."
    echo "  [TIP]  For the best experience, we recommend using the standalone"
    echo "         'Hecos Tray' application to install, manage, and update Hecos."
    echo "  ------------------------------------------------------------------------------"
    echo ""
    read -p "Select an option (1-5): " CH
}

while true; do
    show_menu
    case $CH in
        1)
            echo ""
            echo "[*] Starting Hecos Web UI..."
            if [ -f "scripts/linux/run/hecos_web_run.sh" ]; then
                bash "scripts/linux/run/hecos_web_run.sh"
            else
                echo "[!] Web run script not found."
                read -p "Press enter to continue..."
            fi
            exit 0
            ;;
        2)
            echo ""
            echo "[*] Starting Hecos Console..."
            if [ -f "scripts/linux/run/HECOS_CONSOLE_RUN.sh" ]; then
                bash "scripts/linux/run/HECOS_CONSOLE_RUN.sh"
            else
                echo "[!] Console run script not found."
                read -p "Press enter to continue..."
            fi
            ;;
        3)
            echo ""
            echo "[*] Starting Setup..."
            if [ -f "scripts/linux/setup/INSTALL_HECOS_LINUX.sh" ]; then
                bash "scripts/linux/setup/INSTALL_HECOS_LINUX.sh"
            else
                echo "[!] Setup script not found."
                read -p "Press enter to continue..."
            fi
            ;;
        4)
            echo ""
            echo "[*] Starting Uninstaller..."
            if [ -f "scripts/linux/setup/UNINSTALL_HECOS_LINUX.sh" ]; then
                bash "scripts/linux/setup/UNINSTALL_HECOS_LINUX.sh"
            else
                echo "[!] Uninstaller script not found."
                read -p "Press enter to continue..."
            fi
            ;;
        5)
            exit 0
            ;;
        *)
            ;;
    esac
done
