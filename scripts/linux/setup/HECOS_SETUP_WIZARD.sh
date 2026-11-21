#!/bin/bash
# =============================================================================
# HECOS CORE SETUP WIZARD (Linux / macOS)
# Zero-prerequisite bootstrap: provisions standalone Python 3.11.18 (with
# tkinter, pip, venv, ssl) or creates an isolated venv, installs Core deps
# from pyproject.toml via tomllib, updates shared install.toml, and launches
# the unified setup engine.
# =============================================================================

set -u

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

# --- Parse CLI flags ---
UNATTENDED=0
ARG_TRAY_DIR=""
LAUNCH_MODE="menu"

while [ $# -gt 0 ]; do
    case "$1" in
        --unattended|--silent|-s)
            UNATTENDED=1
            ;;
        --web|--gui)
            LAUNCH_MODE="web"
            ;;
        --doctor)
            LAUNCH_MODE="doctor"
            ;;
        --tray-dir)
            shift
            ARG_TRAY_DIR="${1:-}"
            ;;
        --tray-dir=*)
            ARG_TRAY_DIR="${1#*=}"
            ;;
    esac
    shift || true
done

[ "$UNATTENDED" -eq 1 ] && LAUNCH_MODE="install"

# --- Resolve ROOT_DIR dynamically ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
ROOT_DIR=""
if [ -f "$SCRIPT_DIR/../../../hecos/core/version" ]; then
    ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
elif [ -f "$SCRIPT_DIR/hecos/core/version" ]; then
    ROOT_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../Hecos/hecos/core/version" ]; then
    ROOT_DIR="$(cd "$SCRIPT_DIR/../Hecos" && pwd)"
else
    ROOT_DIR="$SCRIPT_DIR"
fi

mkdir -p "$ROOT_DIR/logs" 2>/dev/null || true
SETUP_LOG="$ROOT_DIR/logs/setup_wizard.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] HECOS CORE SETUP WIZARD STARTED (mode=$LAUNCH_MODE, root=$ROOT_DIR)" >> "$SETUP_LOG"

CORE_VER="unknown"
[ -f "$ROOT_DIR/hecos/core/version" ] && CORE_VER="$(tr -d '\r\n' < "$ROOT_DIR/hecos/core/version")"

# --- Path validation helper ---
validate_path() {
    local p="$1"
    PATH_STATUS="OK"
    PATH_MSG="Safe path"
    local errs=()
    local warns=()

    case "$p" in
        *" "*|*"	"*) errs+=("contains spaces") ;;
    esac
    if printf '%s' "$p" | LC_ALL=C grep -q '[^ -~]'; then
        errs+=("contains non-ASCII characters")
    fi
    if printf '%s' "$p" | grep -qE "[!%^&()=;,\"'\`]"; then
        errs+=("contains unsafe shell characters")
    fi
    case "$p" in
        /tmp/*|/var/tmp/*) warns+=("inside temporary directory") ;;
    esac

    if [ ${#errs[@]} -gt 0 ]; then
        PATH_STATUS="ERR"
        PATH_MSG="$(IFS='; '; echo "${errs[*]}")"
    elif [ ${#warns[@]} -gt 0 ]; then
        PATH_STATUS="WARN"
        PATH_MSG="$(IFS='; '; echo "${warns[*]}")"
    fi
}

# --- Read value from shared install.toml ---
read_registry_key() {
    local key="$1"
    local reg="${XDG_CONFIG_HOME:-$HOME/.config}/hecos/install.toml"
    [ -f "$reg" ] || return 0
    awk -F'=' -v k="$key" '
        $1 ~ "^[[:space:]]*" k "[[:space:]]*$" {
            v = substr($0, index($0, "=") + 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
            gsub(/^[\x27"]|[\x27"]$/, "", v)
            print v
            exit
        }
    ' "$reg"
}

# --- Smart Tray detection ---
detect_tray() {
    TRAY_DIR=""
    TRAY_WARN=0
    local reg_tray
    reg_tray="$(read_registry_key "tray_path")"
    local core_parent
    core_parent="$(dirname "$ROOT_DIR")"

    for cand in \
        "$ARG_TRAY_DIR" \
        "${HECOS_TRAY_DIR:-}" \
        "$reg_tray" \
        "$core_parent/Hecos-Tray" \
        "$HOME/Hecos-Tray" \
        "/opt/hecos-tray"; do
        if [ -n "$cand" ] && [ -f "$cand/tray/version" ]; then
            TRAY_DIR="$cand"
            return 0
        fi
    done

    for parent in "$core_parent" "$HOME"; do
        for cand in "$parent"/Hecos-Tray-*; do
            if [ -f "$cand/tray/version" ]; then
                TRAY_DIR="$cand"
                TRAY_WARN=1
                return 0
            fi
        done
    done
}

# --- Provision python-build-standalone 3.11.18 ---
provision_standalone_python() {
    local target_dir="$1"
    local os_name arch triple
    os_name="$(uname -s)"
    arch="$(uname -m)"

    case "${os_name}:${arch}" in
        Linux:x86_64)   triple="x86_64-unknown-linux-gnu" ;;
        Linux:aarch64|Linux:arm64) triple="aarch64-unknown-linux-gnu" ;;
        Darwin:x86_64)  triple="x86_64-apple-darwin" ;;
        Darwin:arm64)   triple="aarch64-apple-darwin" ;;
        *)
            echo "${C_YELLOW}[WARN]${C_RST} Unsupported arch for standalone Python (${os_name}/${arch})."
            return 1
            ;;
    esac

    local asset="cpython-3.11.18+20261110-${triple}-install_only.tar.gz"
    local url="https://github.com/astral-sh/python-build-standalone/releases/download/20261110/cpython-3.11.18%2B20261110-${triple}-install_only.tar.gz"
    local sums_url="https://github.com/astral-sh/python-build-standalone/releases/download/20261110/SHA256SUMS"
    local tmp_dir
    tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/hecos_py_XXXXXX")"
    local tgz="$tmp_dir/python.tar.gz"
    local sums="$tmp_dir/SHA256SUMS"

    echo "${C_CYAN}[ .. ]${C_RST} Downloading standalone Python 3.11.18 (${triple}, ~47 MB)..."
    if command -v curl &> /dev/null; then
        curl --fail -L --retry 3 --retry-delay 2 --progress-bar -o "$tgz" "$url" || { rm -rf "$tmp_dir"; return 1; }
    elif command -v wget &> /dev/null; then
        wget --tries=3 --show-progress -q -O "$tgz" "$url" || { rm -rf "$tmp_dir"; return 1; }
    else
        echo "${C_RED}[FAIL]${C_RST} Neither curl nor wget is installed."
        rm -rf "$tmp_dir"
        return 1
    fi

    # Best-effort SHA256 verification
    local hash_cmd=""
    if command -v sha256sum &> /dev/null; then
        hash_cmd="sha256sum"
    elif command -v shasum &> /dev/null; then
        hash_cmd="shasum -a 256"
    fi

    if [ -n "$hash_cmd" ]; then
        local fetched=0
        if command -v curl &> /dev/null; then
            curl --fail -sSL --retry 2 -o "$sums" "$sums_url" 2>/dev/null && fetched=1
        elif command -v wget &> /dev/null; then
            wget -q -O "$sums" "$sums_url" 2>/dev/null && fetched=1
        fi
        if [ "$fetched" -eq 1 ]; then
            local expected actual
            expected="$(grep -F "$asset" "$sums" | head -n 1 | awk '{print tolower($1)}')"
            actual="$($hash_cmd "$tgz" | awk '{print tolower($1)}')"
            if [ -n "$expected" ]; then
                if [ "$expected" = "$actual" ]; then
                    echo "${C_GREEN}[ OK ]${C_RST} SHA256 checksum verified."
                else
                    echo "${C_RED}[FAIL]${C_RST} SHA256 checksum MISMATCH! Aborting."
                    rm -rf "$tmp_dir"
                    return 1
                fi
            fi
        else
            echo "${C_YELLOW}[WARN]${C_RST} Could not fetch SHA256SUMS; continuing."
        fi
    fi

    echo "${C_CYAN}[ .. ]${C_RST} Extracting Python into $target_dir ..."
    tar -xzf "$tgz" -C "$tmp_dir" || { rm -rf "$tmp_dir"; return 1; }
    if [ ! -x "$tmp_dir/python/bin/python3" ]; then
        rm -rf "$tmp_dir"
        return 1
    fi

    rm -rf "$target_dir"
    mv "$tmp_dir/python" "$target_dir"
    rm -rf "$tmp_dir"
    echo "${C_GREEN}[ OK ]${C_RST} Standalone Python 3.11.18 installed."
    return 0
}

echo ""
echo "${C_CYAN}==============================================================================${C_RST}"
echo "  ${C_MAG}HECOS CORE SETUP WIZARD${C_RST}   ${C_CYAN}v${CORE_VER}${C_RST}   ${C_DIM}(LINUX)${C_RST}"
echo "${C_CYAN}==============================================================================${C_RST}"
echo ""

# =============================================================================
# [1/5] PATH & SYSTEM CHECK
# =============================================================================
echo "${C_CYAN}[1/5] Path & System Check${C_RST}"
validate_path "$ROOT_DIR"
if [ "$PATH_STATUS" = "ERR" ]; then
    echo "${C_RED}[FAIL]${C_RST} Unsafe installation path: $ROOT_DIR ($PATH_MSG)"
    echo "       Move Hecos to a clean path (e.g. $HOME/Hecos) and run setup again."
    [ "$UNATTENDED" -eq 0 ] && read -r -p "Press Enter to exit..."
    exit 1
elif [ "$PATH_STATUS" = "WARN" ]; then
    echo "${C_YELLOW}[WARN]${C_RST} Path advisory: $PATH_MSG"
else
    echo "${C_GREEN}[ OK ]${C_RST} Install path verified: $ROOT_DIR"
fi

if [ -f "$ROOT_DIR/hecos/core/version" ]; then
    echo "${C_GREEN}[ OK ]${C_RST} Hecos Core v${CORE_VER} detected"
else
    echo "${C_RED}[FAIL]${C_RST} Core files not found at $ROOT_DIR"
fi

detect_tray
if [ -n "$TRAY_DIR" ]; then
    echo "${C_GREEN}[ OK ]${C_RST} Hecos Tray detected: $TRAY_DIR"
    [ "$TRAY_WARN" -eq 1 ] && echo "${C_YELLOW}[WARN]${C_RST} Tray folder has a version suffix (recommended name: Hecos-Tray)"
else
    echo "${C_DIM}[ -- ]${C_RST} Hecos Tray not detected (optional)"
fi
echo ""

# =============================================================================
# [2/5] PYTHON RUNTIME (Zero-prerequisite standalone OR isolated venv)
# =============================================================================
echo "${C_CYAN}[2/5] Python Runtime${C_RST}"
PYTHON_CMD=""
PYTHON_LOC=""

if [ -x "$ROOT_DIR/python_env/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/python_env/bin/python3"
    PYTHON_LOC="Core Portable Environment ($ROOT_DIR/python_env)"
elif [ -x "$ROOT_DIR/venv/bin/python3" ]; then
    PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
    PYTHON_LOC="Core Virtual Environment ($ROOT_DIR/venv)"
fi

if [ -z "$PYTHON_CMD" ]; then
    SYS_PY=""
    command -v python3 &> /dev/null && SYS_PY="$(command -v python3)"

    if [ "$UNATTENDED" -eq 1 ]; then
        echo "${C_CYAN}[ .. ]${C_RST} Provisioning isolated standalone Python 3.11.18..."
        if provision_standalone_python "$ROOT_DIR/python_env"; then
            PYTHON_CMD="$ROOT_DIR/python_env/bin/python3"
            PYTHON_LOC="Core Portable Environment ($ROOT_DIR/python_env)"
        elif [ -n "$SYS_PY" ]; then
            echo "${C_YELLOW}[WARN]${C_RST} Falling back to creating venv with system Python..."
            if "$SYS_PY" -m venv "$ROOT_DIR/venv"; then
                PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
                PYTHON_LOC="Core Virtual Environment ($ROOT_DIR/venv)"
            fi
        fi
    else
        echo "${C_YELLOW}[WARN]${C_RST} No isolated Hecos Python environment found."
        echo ""
        echo "  ${C_CYAN}1.${C_RST} Download Standalone Portable Python 3.11.18 ${C_GREEN}(Recommended - avoids PEP 668 & includes tkinter)${C_RST}"
        if [ -n "$SYS_PY" ]; then
            echo "  ${C_CYAN}2.${C_RST} Create venv using system Python ($("$SYS_PY" --version 2>&1))"
            echo "  ${C_DIM}3. Exit${C_RST}"
            echo ""
            read -r -p "  >> Select option (1-3) [1]: " PY_CH
        else
            echo "  ${C_DIM}2. Exit${C_RST}"
            echo ""
            read -r -p "  >> Select option (1-2) [1]: " PY_CH
            [ "${PY_CH:-1}" = "2" ] && exit 0
        fi
        PY_CH="${PY_CH:-1}"

        if [ "$PY_CH" = "1" ]; then
            if provision_standalone_python "$ROOT_DIR/python_env"; then
                PYTHON_CMD="$ROOT_DIR/python_env/bin/python3"
                PYTHON_LOC="Core Portable Environment ($ROOT_DIR/python_env)"
            elif [ -n "$SYS_PY" ]; then
                echo "${C_YELLOW}[WARN]${C_RST} Standalone download failed. Trying local venv..."
                "$SYS_PY" -m venv "$ROOT_DIR/venv" && PYTHON_CMD="$ROOT_DIR/venv/bin/python3" && PYTHON_LOC="Core Virtual Environment ($ROOT_DIR/venv)"
            fi
        elif [ "$PY_CH" = "2" ] && [ -n "$SYS_PY" ]; then
            echo "${C_CYAN}[ .. ]${C_RST} Creating virtual environment at $ROOT_DIR/venv..."
            if "$SYS_PY" -m venv "$ROOT_DIR/venv"; then
                PYTHON_CMD="$ROOT_DIR/venv/bin/python3"
                PYTHON_LOC="Core Virtual Environment ($ROOT_DIR/venv)"
            else
                echo "${C_RED}[FAIL]${C_RST} Could not create venv. Install venv support for your distro:"
                echo "       Debian/Ubuntu: sudo apt install python3-venv python3-tk portaudio19-dev"
                echo "       Fedora:        sudo dnf install python3-tkinter portaudio-devel"
                echo "       Arch:          sudo pacman -S tk portaudio"
                read -r -p "Press Enter to exit..."
                exit 1
            fi
        else
            exit 0
        fi
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "${C_RED}[FAIL]${C_RST} Could not provision a Python 3.10+ environment."
    echo "       Debian/Ubuntu: sudo apt install python3 python3-venv python3-tk portaudio19-dev"
    echo "       Fedora:        sudo dnf install python3 python3-tkinter portaudio-devel"
    echo "       Arch:          sudo pacman -S python tk portaudio"
    [ "$UNATTENDED" -eq 0 ] && read -r -p "Press Enter to exit..."
    exit 1
fi

echo "${C_GREEN}[ OK ]${C_RST} Python ready: $PYTHON_LOC ($("$PYTHON_CMD" --version 2>&1))"
echo ""

# =============================================================================
# [3/5] CORE DEPENDENCIES (via tomllib in hecos/setup/setup_env.py)
# =============================================================================
echo "${C_CYAN}[3/5] Core Dependencies${C_RST}"
cd "$ROOT_DIR" || exit 1

if [ "$LAUNCH_MODE" != "doctor" ]; then
    echo "${C_CYAN}[ .. ]${C_RST} Syncing Python packages from pyproject.toml..."
    "$PYTHON_CMD" "hecos/setup_wizard.py" --install-deps
    DEPS_RC=$?
    if [ "$DEPS_RC" -ne 0 ]; then
        echo "${C_RED}[FAIL]${C_RST} Essential dependency installation failed (exit code $DEPS_RC)."
        echo "       Linux audio hint: sudo apt install portaudio19-dev (or dnf portaudio-devel)"
        [ "$UNATTENDED" -eq 0 ] && read -r -p "Press Enter to exit..."
        exit 1
    fi
    echo "${C_GREEN}[ OK ]${C_RST} Core dependencies verified."
fi
echo ""

# =============================================================================
# [4/5] INSTALL REGISTRY
# =============================================================================
echo "${C_CYAN}[4/5] Install Registry${C_RST}"
TRAY_ARGS=()
if [ -n "$TRAY_DIR" ]; then
    export HECOS_TRAY_DIR="$TRAY_DIR"
    TRAY_ARGS=(--tray-dir "$TRAY_DIR")
fi
"$PYTHON_CMD" -c "import sys; sys.path.insert(0, sys.argv[1]); from hecos.setup.setup_env import register_installation; print('[ OK ] Registered in:', register_installation())" "$ROOT_DIR"
echo ""

# =============================================================================
# [5/5] LAUNCH SETUP INTERFACE
# =============================================================================
echo "${C_CYAN}[5/5] Launching Setup Interface${C_RST}"
case "$LAUNCH_MODE" in
    install)
        "$PYTHON_CMD" "hecos/setup_wizard.py" install --unattended --skip-deps "${TRAY_ARGS[@]}"
        WIZ_RC=$?
        ;;
    web)
        "$PYTHON_CMD" "hecos/setup_wizard.py" --web "${TRAY_ARGS[@]}"
        WIZ_RC=$?
        ;;
    doctor)
        "$PYTHON_CMD" "hecos/setup_wizard.py" doctor "${TRAY_ARGS[@]}"
        WIZ_RC=$?
        ;;
    *)
        "$PYTHON_CMD" "hecos/setup_wizard.py" menu "${TRAY_ARGS[@]}"
        WIZ_RC=$?
        ;;
esac

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Setup wizard finished with code $WIZ_RC" >> "$SETUP_LOG"
exit "$WIZ_RC"
