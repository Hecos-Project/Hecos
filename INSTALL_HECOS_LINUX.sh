#!/bin/bash
# =============================================================================
# HECOS OFFICIAL UNIFIED INSTALLER (Linux / macOS)
# Works in ALL 3 modes:
#   1. Standalone file:   bash INSTALL_HECOS_LINUX.sh
#   2. One-liner pipe:    curl -fsSL https://raw.githubusercontent.com/Hecos-Project/Hecos/main/INSTALL_HECOS_LINUX.sh | bash
#   3. Inside Hecos dir:  ./INSTALL_HECOS_LINUX.sh [--cli | --unattended | --web]
#
# Automatically provisions Portable Python 3.11.18 (with tkinter & pip) if
# Python 3.10+ is missing, verifies SHA256, and opens the Graphical Setup
# Wizard in a native Chromium/Edge app window (or CLI fallback on headless
# Linux servers without DISPLAY/WAYLAND_DISPLAY).
# =============================================================================

set -u

if [ -t 1 ]; then
    C_CYAN=$'\033[96m'; C_MAG=$'\033[95m'; C_GREEN=$'\033[92m'
    C_YELLOW=$'\033[93m'; C_RED=$'\033[91m'; C_DIM=$'\033[90m'; C_RST=$'\033[0m'
else
    C_CYAN=""; C_MAG=""; C_GREEN=""; C_YELLOW=""; C_RED=""; C_DIM=""; C_RST=""
fi

# Safe under both direct execution and `curl ... | bash` (even with set -u on Bash 4/5)
set +u
SCRIPT_PATH="${BASH_SOURCE[0]:-}"
set -u
SCRIPT_DIR=""
LOCAL_MODE=0
if [ -n "$SCRIPT_PATH" ] && [ -f "$SCRIPT_PATH" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" &> /dev/null && pwd)"
    [ -f "$SCRIPT_DIR/hecos/setup/web_ui/server.py" ] && LOCAL_MODE=1
fi

FORCE_CLI=0
FORCE_WEB=0
UNATTENDED=0
for arg in "$@"; do
    case "$arg" in
        --cli) FORCE_CLI=1 ;;
        --web|--gui) FORCE_WEB=1 ;;
        --unattended|--silent|-s) UNATTENDED=1; FORCE_CLI=1 ;;
    esac
done

echo ""
echo "${C_CYAN}==============================================================================${C_RST}"
echo "  ${C_MAG}HECOS OFFICIAL UNIFIED INSTALLER${C_RST}   ${C_CYAN}(Core + Tray — Linux/macOS)${C_RST}"
echo "${C_CYAN}==============================================================================${C_RST}"
echo ""

if [ "$LOCAL_MODE" -eq 1 ]; then
    echo "${C_GREEN}[ OK ]${C_RST} Local Hecos Core detected at $SCRIPT_DIR"
else
    echo "${C_CYAN}[ .. ]${C_RST} Standalone bootstrap mode (no local files required)"
fi

# Non-blocking Linux system checks (helpful hints, never blocks install)
if [ "$(uname -s)" = "Linux" ]; then
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        echo "${C_RED}[FAIL]${C_RST} Neither curl nor wget is installed. Install curl first:"
        echo "       Debian/Ubuntu: sudo apt install curl"
        echo "       Fedora:        sudo dnf install curl"
        echo "       Arch:          sudo pacman -S curl"
        exit 1
    fi
    if ! command -v tar &> /dev/null; then
        echo "${C_YELLOW}[WARN]${C_RST} 'tar' not found — needed if Python must be auto-provisioned."
    fi
fi

fetch_url() {
    local url="$1" dst="$2"
    if command -v curl &> /dev/null; then
        curl --fail -sSL --retry 2 -o "$dst" "$url"
    elif command -v wget &> /dev/null; then
        wget -q --tries=2 -O "$dst" "$url"
    else
        return 1
    fi
}

provision_bootstrap_python() {
    local target_dir="$1"
    local os_name arch triple
    os_name="$(uname -s)"
    arch="$(uname -m)"
    case "${os_name}:${arch}" in
        Linux:x86_64)              triple="x86_64-unknown-linux-gnu" ;;
        Linux:aarch64|Linux:arm64) triple="aarch64-unknown-linux-gnu" ;;
        Darwin:x86_64)             triple="x86_64-apple-darwin" ;;
        Darwin:arm64)              triple="aarch64-apple-darwin" ;;
        *)
            echo "${C_RED}[FAIL]${C_RST} Unsupported platform for standalone Python: ${os_name}/${arch}"
            return 1
            ;;
    esac

    local asset="cpython-3.11.18+20261110-${triple}-install_only.tar.gz"
    local url="https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.11.18%2B20261110-${triple}-install_only.tar.gz"
    local sums_url="https://github.com/astral-sh/python-build-standalone/releases/download/20261110/SHA256SUMS"
    local tmp_dir
    tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/hecos_boot_py_XXXXXX")"
    local tgz="$tmp_dir/py.tar.gz"
    local sums="$tmp_dir/SHA256SUMS"

    echo "${C_CYAN}[ .. ]${C_RST} Downloading Portable Python 3.11.18 (${triple}, ~47 MB)..."
    if command -v curl &> /dev/null; then
        curl --fail -L --retry 3 --progress-bar -o "$tgz" "$url" || { rm -rf "$tmp_dir"; return 1; }
    elif command -v wget &> /dev/null; then
        wget --tries=3 --show-progress -q -O "$tgz" "$url" || { rm -rf "$tmp_dir"; return 1; }
    else
        rm -rf "$tmp_dir"; return 1
    fi

    local hash_cmd=""
    command -v sha256sum &> /dev/null && hash_cmd="sha256sum"
    [ -z "$hash_cmd" ] && command -v shasum &> /dev/null && hash_cmd="shasum -a 256"
    if [ -n "$hash_cmd" ] && fetch_url "$sums_url" "$sums"; then
        local exp act
        exp="$(grep -F "$asset" "$sums" | head -n 1 | awk '{print tolower($1)}')"
        act="$($hash_cmd "$tgz" | awk '{print tolower($1)}')"
        if [ -n "$exp" ] && [ "$exp" != "$act" ]; then
            echo "${C_RED}[FAIL]${C_RST} SHA256 checksum mismatch! Aborting."
            rm -rf "$tmp_dir"; return 1
        fi
        [ -n "$exp" ] && echo "${C_GREEN}[ OK ]${C_RST} SHA256 checksum verified."
    fi

    echo "${C_CYAN}[ .. ]${C_RST} Extracting Portable Python..."
    tar -xzf "$tgz" -C "$tmp_dir" || { rm -rf "$tmp_dir"; return 1; }
    [ -x "$tmp_dir/python/bin/python3" ] || { rm -rf "$tmp_dir"; return 1; }
    mkdir -p "$(dirname "$target_dir")"
    rm -rf "$target_dir"
    mv "$tmp_dir/python" "$target_dir"
    rm -rf "$tmp_dir"
    return 0
}

# --- [1/3] Find compatible Python 3.10+ (or auto-provision) ---
echo "${C_CYAN}[1/3] Checking Python bootstrap runtime...${C_RST}"
BOOT_PY="${XDG_DATA_HOME:-$HOME/.local/share}/hecos/bootstrap_py"
PYTHON_CMD=""

check_py() {
    [ -n "${1:-}" ] && [ -x "$1" ] && "$1" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" &> /dev/null
}
check_py_cmd() {
    command -v "$1" &> /dev/null && "$1" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" &> /dev/null
}

if [ "$LOCAL_MODE" -eq 1 ] && check_py "$SCRIPT_DIR/python_env/bin/python3"; then
    PYTHON_CMD="$SCRIPT_DIR/python_env/bin/python3"
elif check_py "$BOOT_PY/bin/python3"; then
    PYTHON_CMD="$BOOT_PY/bin/python3"
elif check_py "$HOME/Hecos/python_env/bin/python3"; then
    PYTHON_CMD="$HOME/Hecos/python_env/bin/python3"
elif check_py_cmd "python3"; then
    PYTHON_CMD="$(command -v python3)"
elif check_py_cmd "python"; then
    PYTHON_CMD="$(command -v python)"
else
    echo "${C_YELLOW}[WARN]${C_RST} No Python 3.10+ found. Provisioning Portable Python 3.11.18..."
    if provision_bootstrap_python "$BOOT_PY"; then
        PYTHON_CMD="$BOOT_PY/bin/python3"
    else
        echo "${C_RED}[FAIL]${C_RST} Could not provision Python 3.10+. Install python3 and retry."
        exit 1
    fi
fi

echo "${C_GREEN}[ OK ]${C_RST} Bootstrap Python ready ($("$PYTHON_CMD" --version 2>&1))"

# --- Detect headless Linux server (no X11/Wayland display) ---
IS_HEADLESS=0
if [ "$(uname -s)" = "Linux" ] && [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; then
    IS_HEADLESS=1
fi

# --- [2/3] Launch local or standalone UI ---
if [ "$LOCAL_MODE" -eq 1 ]; then
    cd "$SCRIPT_DIR" || exit 1
    if [ "$UNATTENDED" -eq 1 ]; then
        echo "${C_CYAN}[2/3] Running unattended local Core setup...${C_RST}"
        exec bash "$SCRIPT_DIR/scripts/linux/setup/HECOS_SETUP_WIZARD.sh" --unattended
    elif [ "$FORCE_CLI" -eq 1 ]; then
        echo "${C_CYAN}[2/3] Launching local CLI Setup Wizard...${C_RST}"
        exec bash "$SCRIPT_DIR/scripts/linux/setup/HECOS_SETUP_WIZARD.sh"
    fi
    echo "${C_CYAN}[2/3] Using local Setup UI...${C_RST}"
    if [ "$IS_HEADLESS" -eq 1 ] && [ "$FORCE_WEB" -eq 0 ]; then
        echo "${C_YELLOW}[WARN]${C_RST} Headless Linux detected (no DISPLAY/WAYLAND_DISPLAY)."
        echo "       Launching CLI Setup Wizard (pass --web to start the web server for SSH tunneling)."
        exec bash "$SCRIPT_DIR/scripts/linux/setup/HECOS_SETUP_WIZARD.sh"
    fi
    echo "${C_CYAN}[3/3] Opening Hecos Graphical Setup Wizard...${C_RST}"
    exec "$PYTHON_CMD" "hecos/setup_wizard.py" --web "$@"
fi

echo "${C_CYAN}[2/3] Fetching lightweight Graphical Installer UI (~145 KB)...${C_RST}"
UI_DIR="$(mktemp -d "${TMPDIR:-/tmp}/hecos_installer_ui_XXXXXX")"
trap 'rm -rf "$UI_DIR"' EXIT
mkdir -p "$UI_DIR/hecos/setup/web_ui" "$UI_DIR/hecos/assets"
: > "$UI_DIR/hecos/__init__.py"

RAW_BASE="https://raw.githubusercontent.com/Hecos-Project/Hecos/main"
FILES=(
    "hecos/setup/__init__.py"
    "hecos/setup/main.py"
    "hecos/setup/i18n.py"
    "hecos/setup/install_registry.py"
    "hecos/setup/utils.py"
    "hecos/setup/unified_installer.py"
    "hecos/setup/web_ui/__init__.py"
    "hecos/setup/web_ui/state.py"
    "hecos/setup/web_ui/styles.py"
    "hecos/setup/web_ui/templates.py"
    "hecos/setup/web_ui/server.py"
)

for rel in "${FILES[@]}"; do
    if ! fetch_url "$RAW_BASE/$rel" "$UI_DIR/$rel"; then
        echo "${C_RED}[FAIL]${C_RST} Could not download $rel from GitHub."
        exit 1
    fi
done
fetch_url "$RAW_BASE/hecos/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" "$UI_DIR/hecos/assets/Hecos_Logo_SQR_NBG_LogoOnly.png" || true

echo "${C_GREEN}[ OK ]${C_RST} Graphical Installer UI ready."
if [ "$IS_HEADLESS" -eq 1 ]; then
    echo "${C_YELLOW}[INFO]${C_RST} Headless Linux detected: the installer web server will listen on 127.0.0.1."
    echo "${C_DIM}       Tip: forward the printed port over SSH (ssh -L 8080:127.0.0.1:8080 user@host).${C_RST}"
fi
echo "${C_CYAN}[3/3] Opening Hecos Graphical Setup Wizard...${C_RST}"
echo ""
"$PYTHON_CMD" -c "import sys, runpy; sys.path.insert(0, sys.argv[1]); sys.argv=['hecos.setup.main','--web','--standalone']; runpy.run_module('hecos.setup.main', run_name='__main__')" "$UI_DIR"
