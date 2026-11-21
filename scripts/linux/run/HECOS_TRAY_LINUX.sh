#!/bin/bash
# Locate and launch Hecos Tray on Linux via shared install.toml / standard paths
set -u
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CORE_PARENT="$(dirname "$ROOT_DIR")"

REG_TRAY=""
REG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/hecos/install.toml"
if [ -f "$REG_FILE" ]; then
    REG_TRAY="$(awk -F'=' '$1 ~ /^[[:space:]]*tray_path[[:space:]]*$/ { v=substr($0,index($0,"=")+1); gsub(/^[[:space:]]+|[[:space:]]+$/,"",v); gsub(/^[\x27"]|[\x27"]$/,"",v); print v; exit }' "$REG_FILE")"
fi

for cand in "${HECOS_TRAY_DIR:-}" "$REG_TRAY" "$CORE_PARENT/Hecos-Tray" "$HOME/Hecos-Tray" "/opt/hecos-tray"; do
    if [ -n "$cand" ] && [ -f "$cand/START_HECOS_TRAY_LINUX.sh" ]; then
        exec bash "$cand/START_HECOS_TRAY_LINUX.sh" "$@"
    fi
done

echo "[FAIL] Could not find Hecos-Tray (START_HECOS_TRAY_LINUX.sh)."
exit 1
