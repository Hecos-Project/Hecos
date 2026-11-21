#!/bin/bash
# Hecos Native Web Interface Launcher (Linux / macOS)

set -u

if [ -t 1 ]; then
    C_CYAN=$'\033[96m'; C_MAG=$'\033[95m'; C_GREEN=$'\033[92m'
    C_YELLOW=$'\033[93m'; C_RED=$'\033[91m'; C_DIM=$'\033[90m'; C_RST=$'\033[0m'
else
    C_CYAN=""; C_MAG=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_DIM=""; C_RST=""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
if [ -f "$SCRIPT_DIR/hecos/core/version" ]; then
    ROOT_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../../../hecos/core/version" ]; then
    ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
else
    ROOT_DIR="$HOME/Hecos"
fi
cd "$ROOT_DIR" || exit 1

HECOS_VERSION="Unknown"
[ -f "hecos/core/version" ] && HECOS_VERSION="$(tr -d '\r\n' < hecos/core/version)"

echo ""
echo "${C_CYAN}==============================================================${C_RST}"
echo "  ${C_MAG}HECOS NATIVE WEB INTERFACE${C_RST}   ${C_CYAN}v${HECOS_VERSION}${C_RST}"
echo "${C_CYAN}==============================================================${C_RST}"
echo ""

PYTHON_CMD=""
if [ -x "$ROOT_DIR/python_env/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/python_env/bin/python3"
elif [ -x "$ROOT_DIR/python_env/bin/python" ]; then
    PYTHON_CMD="$ROOT_DIR/python_env/bin/python"
elif [ -x "$ROOT_DIR/venv/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
elif [ -x "$ROOT_DIR/venv/bin/python" ]; then
    PYTHON_CMD="$ROOT_DIR/venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="$(command -v python3)"
elif command -v python &> /dev/null; then
    PYTHON_CMD="$(command -v python)"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "${C_RED}[FAIL]${C_RST} Python not found. Run ./INSTALL_HECOS_LINUX.sh or scripts/linux/setup/HECOS_SETUP_WIZARD.sh first."
    exit 1
fi

LAN_IP="$("$PYTHON_CMD" -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254', 1)); print(s.getsockname()[0])" 2>/dev/null || echo "localhost")"
SCHEME="$("$PYTHON_CMD" -c "import yaml; print('https' if yaml.safe_load(open('hecos/config/data/system.yaml', encoding='utf-8')).get('plugins',{}).get('WEB_UI',{}).get('https_enabled',False) else 'http')" 2>/dev/null || echo "http")"

echo "${C_CYAN}==============================================================${C_RST}"
echo "  ${C_MAG}[ QUICK ACCESS ]${C_RST}"
echo "  ${C_DIM}Connect from this PC, phone, or tablet on your LAN:${C_RST}"
echo ""
echo "  * Chat:     ${C_GREEN}${SCHEME}://${LAN_IP}:7070/chat${C_RST}"
echo "  * Config:   ${C_GREEN}${SCHEME}://${LAN_IP}:7070/hecos/config/ui${C_RST}"
echo "  * Drive:    ${C_GREEN}${SCHEME}://${LAN_IP}:7070/drive${C_RST}"
echo "${C_CYAN}==============================================================${C_RST}"
echo ""

export HECOS_BOOT_MODE="webui"
exec "$PYTHON_CMD" hecos/monitor.py --script hecos.modules.web_ui.server
