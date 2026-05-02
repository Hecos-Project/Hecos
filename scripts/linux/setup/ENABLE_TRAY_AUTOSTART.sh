#!/bin/bash
echo "=================================================="
echo "  HECOS CORE - ENABLE TRAY AUTOSTART (LINUX)"
echo "=================================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HECOS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TRAY_RUNNER="$HECOS_ROOT/scripts/linux/run/HECOS_TRAY_LINUX.sh"

if [ ! -f "$TRAY_RUNNER" ]; then
    echo "[!] ERROR: Could not find HECOS_TRAY_LINUX.sh at:"
    echo "    $TRAY_RUNNER"
    exit 1
fi

chmod +x "$TRAY_RUNNER"

AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
DESKTOP_FILE="$AUTOSTART_DIR/hecos-core-tray.desktop"

echo "[*] Writing XDG Desktop Entry..."
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Exec=bash "$TRAY_RUNNER"
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Hecos
Comment=Hecos Agentic Layer Tray
Icon=$HECOS_ROOT/hecos/assets/Hecos_Core_Logo_NBG.png
Terminal=false
EOF

chmod +x "$DESKTOP_FILE"

echo ""
echo "[+] Done! Hecos Tray natively added to Linux autostart."
echo "    Path: $DESKTOP_FILE"
echo ""
