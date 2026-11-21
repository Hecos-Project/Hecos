#!/bin/bash
# Hecos Global Launcher for Linux / macOS

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR" || exit 1

# --- Cyber ANSI Palette (TTY-aware) ---
if [ -t 1 ]; then
    C_CYAN=$'\033[96m'
    C_MAG=$'\033[95m'
    C_GREEN=$'\033[92m'
    C_YELLOW=$'\033[93m'
    C_RED=$'\033[91m'
    C_DIM=$'\033[90m'
    C_WHITE=$'\033[97m'
    C_RST=$'\033[0m'
else
    C_CYAN=""; C_MAG=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_DIM=""; C_WHITE=""; C_RST=""
fi

detect_python() {
    if [ -x "$SCRIPT_DIR/python_env/bin/python3" ]; then
        PYTHON_CMD="$SCRIPT_DIR/python_env/bin/python3"
        PY_STATUS="${C_GREEN}Portable (python_env)${C_RST}"
    elif [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
        PYTHON_CMD="$SCRIPT_DIR/venv/bin/python3"
        PY_STATUS="${C_GREEN}Virtual Env (venv)${C_RST}"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PY_STATUS="${C_YELLOW}System (python3)${C_RST}"
    else
        PYTHON_CMD=""
        PY_STATUS="${C_YELLOW}Not configured (run Option 1)${C_RST}"
    fi
}

show_menu() {
    while true; do
        HECOS_VER="unknown"
        [ -f "$SCRIPT_DIR/hecos/core/version" ] && HECOS_VER="$(tr -d '\r\n' < "$SCRIPT_DIR/hecos/core/version")"
        detect_python

        clear 2>/dev/null || true
        echo ""
        echo "${C_CYAN}==============================================================================${C_RST}"
        echo "  ${C_MAG}HECOS GLOBAL LAUNCHER${C_RST}   ${C_CYAN}v${HECOS_VER}${C_RST}   ${C_DIM}(LINUX)${C_RST}"
        echo "${C_CYAN}==============================================================================${C_RST}"
        echo "  ${C_DIM}Core Path :${C_RST} ${C_WHITE}${SCRIPT_DIR}${C_RST}"
        echo "  ${C_DIM}Python    :${C_RST} ${PY_STATUS}"
        echo "${C_CYAN}------------------------------------------------------------------------------${C_RST}"
        echo ""
        echo "  ${C_CYAN}1.${C_RST} ${C_WHITE}Install / Setup Wizard${C_RST}       ${C_DIM}(Python, deps, Piper TTS, repair)${C_RST}"
        echo "  ${C_CYAN}2.${C_RST} ${C_WHITE}Start Hecos (Web UI)${C_RST}         ${C_DIM}(Native web server)${C_RST}"
        echo "  ${C_CYAN}3.${C_RST} ${C_WHITE}Start Hecos (Console)${C_RST}        ${C_DIM}(Interactive text terminal)${C_RST}"
        echo "  ${C_CYAN}4.${C_RST} ${C_WHITE}System Diagnostics (Doctor)${C_RST}  ${C_DIM}(Verify Python, deps, paths, Tray)${C_RST}"
        echo "  ${C_DIM}5. Exit${C_RST}"
        echo ""
        echo "${C_DIM}------------------------------------------------------------------------------${C_RST}"
        echo "  ${C_DIM}[INFO] Advanced scripts live inside the 'scripts' folder.${C_RST}"
        echo "  ${C_DIM}[TIP]  Use 'Hecos Tray' to install, manage, and update Hecos.${C_RST}"
        echo "${C_DIM}------------------------------------------------------------------------------${C_RST}"
        echo ""
        read -r -p "  >> Select an option (1-5): " choice

        case "${choice:-}" in
            1)
                echo ""
                echo "${C_CYAN}[ >> ]${C_RST} Launching Setup Wizard..."
                if [ -f "scripts/linux/setup/HECOS_SETUP_WIZARD.sh" ]; then
                    bash "scripts/linux/setup/HECOS_SETUP_WIZARD.sh"
                else
                    echo "${C_RED}[FAIL]${C_RST} Setup script not found."
                    read -r -p "Press Enter to continue..."
                fi
                ;;
            2)
                echo ""
                echo "${C_CYAN}[ >> ]${C_RST} Starting Hecos Web UI..."
                if [ -f "scripts/linux/run/HECOS_WEBUI_RUN_LINUX.sh" ]; then
                    bash "scripts/linux/run/HECOS_WEBUI_RUN_LINUX.sh"
                else
                    echo "${C_RED}[FAIL]${C_RST} Web run script not found."
                    read -r -p "Press Enter to continue..."
                fi
                ;;
            3)
                echo ""
                echo "${C_CYAN}[ >> ]${C_RST} Starting Hecos Console..."
                if [ -f "scripts/linux/run/HECOS_CONSOLE_RUN.sh" ]; then
                    bash "scripts/linux/run/HECOS_CONSOLE_RUN.sh"
                else
                    echo "${C_RED}[FAIL]${C_RST} Console run script not found."
                    read -r -p "Press Enter to continue..."
                fi
                ;;
            4)
                echo ""
                if [ -z "$PYTHON_CMD" ]; then
                    echo "${C_YELLOW}[WARN]${C_RST} Python not installed yet. Run Option 1 first."
                else
                    "$PYTHON_CMD" "hecos/setup_wizard.py" doctor
                fi
                echo ""
                read -r -p "Press Enter to continue..."
                ;;
            5)
                exit 0
                ;;
            *)
                ;;
        esac
    done
}

show_menu
