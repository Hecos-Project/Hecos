#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  ZENTRA CORE — SERVICE UNINSTALLER (Linux/systemd)
# ═══════════════════════════════════════════════════════════

set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$INSTALL_DIR/python_env/bin/python" ]; then
    PYTHON="$INSTALL_DIR/python_env/bin/python"
elif [ -f "$INSTALL_DIR/venv/bin/python" ]; then
    PYTHON="$INSTALL_DIR/venv/bin/python"
else
    PYTHON=$(which python3)
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ZENTRA CORE — Service Uninstaller (Linux)"
echo "═══════════════════════════════════════════════════"
echo ""
echo "[*] Stopping and removing Zentra Core service..."
$PYTHON "$INSTALL_DIR/scripts/install_as_service.py" --uninstall

echo ""
echo "[+] Service removed successfully."
echo "[*] You can still use Zentra manually with: bash zentra_web_run.sh"
echo ""
