#!/bin/bash
# Enable Hecos Tray autostart via XDG desktop entry (Linux)

set -u

echo "=================================================="
echo "  HECOS CORE - ENABLE TRAY AUTOSTART (LINUX)"
echo "=================================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HECOS_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CORE_PARENT="$(dirname "$HECOS_ROOT")"

# Read tray_path from shared install.toml if present
REG_TRAY=""
REG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/hecos/install.toml"
if [ -f "$REG_FILE" ]; then
    REG_TRAY="$(awk -F'=' '$1 ~ /^[[:space:]]*tray_path[[:space:]]*$/ { v=substr($0,index($0,"=")+1); gsub(/^[[:space:]]+|[[:space:]]+$/,"",v); gsub(/^[\x27"]|[\x27"]$/,"",v); print v; exit }' "$REG_FILE")"
fi

TRAY_DIR=""
for cand in "${HECOS_TRAY_DIR:-}" "$REG_TRAY" "$CORE_PARENT/Hecos-Tray" "$HOME/Hecos-Tray" "/opt/hecos-tray"; do
    if [ -n "$cand" ] && [ -f "$cand/START_HECOS_TRAY_LINUX.sh" ]; then
        TRAY_DIR="$cand"
        break
    fi
done

if [ -z "$TRAY_DIR" ]; then
    echo "[FAIL] Could not find START_HECOS_TRAY_LINUX.sh in any known Hecos-Tray folder."
    exit 1
fi

TRAY_RUNNER="$TRAY_DIR/START_HECOS_TRAY_LINUX.sh"
chmod +x "$TRAY_RUNNER"

AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
mkdir -p "$AUTOSTART_DIR"
DESKTOP_FILE="$AUTOSTART_DIR/hecos-tray.desktop"

ICON_PATH="$HECOS_ROOT/hecos/assets/Hecos_Core_Logo_NBG.png"
[ -f "$TRAY_DIR/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" ] && ICON_PATH="$TRAY_DIR/assets/Hecos_Logo_SQR_NBG_LogoOnly.png"

echo "[ .. ] Writing XDG Desktop Entry..."
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Exec=bash "$TRAY_RUNNER"
Path=$TRAY_DIR
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Hecos
Comment=Hecos Agentic Layer Tray
Icon=$ICON_PATH
Terminal=false
EOF

chmod +x "$DESKTOP_FILE"

echo ""
echo "[ OK ] Hecos Tray added to Linux autostart."
echo "       Entry:  $DESKTOP_FILE"
echo "       Runner: $TRAY_RUNNER"
echo ""
exit 0
