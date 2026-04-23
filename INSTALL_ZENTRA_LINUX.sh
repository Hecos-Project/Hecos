#!/bin/bash
# Zentra Core - Portable Setup for Linux

echo "=============================================================================="
echo "                     ZENTRA CORE - PORTABLE INSTALLER (LINUX)"
echo "=============================================================================="
echo "Questo script configurera un ambiente virtuale isolato per Python e "
echo "scarichera Piper TTS nella cartella 'bin/piper'."
echo "Nessuna installazione globale verra modificata."
echo "=============================================================================="
echo ""

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$ROOT_DIR"

# Vars
PYTHON_ENV_DIR="$ROOT_DIR/python_env"
PIPER_DIR="$ROOT_DIR/bin/piper"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
PIPER_VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/aurora/medium/it_IT-aurora-medium.onnx"
PIPER_VOICE_JSON="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/it/it_IT/aurora/medium/it_IT-aurora-medium.onnx.json"

# Check Python availability
if ! command -v python3 &> /dev/null; then
    echo "[!] Python3 non trovato. Installa Python3 (es. sudo apt install python3 python3-venv) per procedere."
    exit 1
fi

# 1. Create Virtual Environment
if [ ! -d "$PYTHON_ENV_DIR" ]; then
    echo "[*] Creazione ambiente Python isolato in $PYTHON_ENV_DIR..."
    python3 -m venv "$PYTHON_ENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[!] Fallimento nella creazione del venv. Prova a eseguire: sudo apt install python3-venv"
        exit 1
    fi
else
    echo "[+] Ambiente Python isolato esistente."
fi

# 2. Install Dependencies
echo ""
echo "[*] Installazione dipendenze in corso..."
"$PYTHON_ENV_DIR/bin/pip" install --upgrade pip
"$PYTHON_ENV_DIR/bin/pip" install -r requirements.txt

# 3. Download Piper TTS
echo ""
if [ ! -f "$PIPER_DIR/piper" ]; then
    echo "[*] Download Piper TTS (Linux_x86_64)..."
    mkdir -p "$ROOT_DIR/bin"
    wget -qO piper.tar.gz "$PIPER_URL"
    tar -xzf piper.tar.gz -C "$ROOT_DIR/bin"
    rm piper.tar.gz
    # The tarball extracts a folder natively called "piper"
    chmod +x "$PIPER_DIR/piper"
else
    echo "[+] Piper TTS gia presente."
fi

# 4. Download Default Italian Voice
echo ""
if [ ! -f "$PIPER_DIR/it_IT-aurora-medium.onnx" ]; then
    echo "[*] Download modello voce Italiano..."
    wget -qO "$PIPER_DIR/it_IT-aurora-medium.onnx" "$PIPER_VOICE_URL"
    wget -qO "$PIPER_DIR/it_IT-aurora-medium.onnx.json" "$PIPER_VOICE_JSON"
else
    echo "[+] Modello voce esistente."
fi

# 5. Create Desktop Entry (Optional)
echo ""
echo "[*] Generazione del file .desktop..."
DESKTOP_FILE="$HOME/.local/share/applications/zentra-core.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Zentra AI
Comment=Zentra Web UI
Exec=$ROOT_DIR/zentra_web_run.sh
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Development;
EOF
chmod +x "$DESKTOP_FILE"
echo "[+] Creato collegamento applicazione in menu: Zentra AI"


echo "=============================================================================="
echo "[SUCCESS] Installazione completata!"
echo ""
echo "Per avviare Zentra esegui ./zentra_web_run.sh"
echo "Oppure avvia 'Zentra AI' dal menu delle tue applicazioni."
echo "=============================================================================="
