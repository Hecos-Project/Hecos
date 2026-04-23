#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  ZENTRA CORE — SERVICE INSTALLER (Linux/systemd)
#  Native Modular AI Operating System
# ═══════════════════════════════════════════════════════════

set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       ZENTRA CORE — SERVICE INSTALLER           ║${NC}"
echo -e "${CYAN}║       Native Modular AI Operating System        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─────────────────────────────────────────────────────
# STEP 1: Find Python
# ─────────────────────────────────────────────────────
if [ -f "$INSTALL_DIR/python_env/bin/python" ]; then
    PYTHON="$INSTALL_DIR/python_env/bin/python"
    echo -e "${GREEN}[+] Using portable Python: $PYTHON${NC}"
elif [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    PYTHON="$INSTALL_DIR/venv/bin/python"
    echo -e "${GREEN}[+] Using virtualenv Python: $PYTHON${NC}"
else
    PYTHON=$(which python3 || which python)
    echo -e "${YELLOW}[*] Using system Python: $PYTHON${NC}"
fi
echo ""

# ─────────────────────────────────────────────────────
# STEP 2: Install service dependencies
# ─────────────────────────────────────────────────────
echo -e "${CYAN}[*] Installing required packages (pystray, pillow)...${NC}"
$PYTHON -m pip install pystray pillow --quiet
echo -e "${GREEN}[+] Dependencies installed.${NC}"
echo ""

# ─────────────────────────────────────────────────────
# STEP 3: Install systemd user service
# ─────────────────────────────────────────────────────
echo -e "${CYAN}[*] Installing Zentra Core as a systemd user service...${NC}"
$PYTHON "$INSTALL_DIR/scripts/install_as_service.py" --install
echo ""

# ─────────────────────────────────────────────────────
# STEP 4: Enable lingering (service starts before login)
# ─────────────────────────────────────────────────────
echo -e "${CYAN}[*] Enabling user lingering (service survives logout)...${NC}"
loginctl enable-linger "$USER" 2>/dev/null || echo -e "${YELLOW}[!] Lingering not available (may require sudo).${NC}"
echo ""

# ─────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────
LAN_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.254.254.254',1)); print(s.getsockname()[0])" 2>/dev/null || echo "N/A")

echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ✔  Installation Complete!                     ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║   • Zentra Core is now a systemd user service   ║${NC}"
echo -e "${GREEN}║   • It will start automatically at next login   ║${NC}"
echo -e "${GREEN}║   • Tray icon registered in XDG autostart       ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║   Access:  http://$LAN_IP:7070/chat             ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║   Check:   systemctl --user status zentra       ║${NC}"
echo -e "${GREEN}║   Logs:    journalctl --user -u zentra -f        ║${NC}"
echo -e "${GREEN}║   Stop:    systemctl --user stop zentra          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
