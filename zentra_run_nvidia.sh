#!/bin/bash
# ZENTRA CORE - Backend VULKAN (Nvidia mode/Ollama)

cd "$(dirname "$0")"

echo "======================================================"
echo "   ATTIVAZIONE VULKAN - MACCHINA LINUX (Nvidia)"
echo "======================================================"

# --- VARIABILI CRITICHE: SBLOCCO VULKAN ---
export OLLAMA_VULKAN=1
export OLLAMA_LLM_LIBRARY=vulkan

# --- OTTIMIZZAZIONE VRAM ---
export OLLAMA_GPU_OVERHEAD=1
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_KEEP_ALIVE=-1

echo "[1/3] Pulizia logica dei processi precedenti (ollama serve)..."
pkill -f "ollama serve"

echo "[2/3] Avvio server Ollama in background..."
ollama serve &

echo "[3/3] Attesa inizializzazione Driver Vulkan (12 secondi)..."
sleep 12

echo "Lancio Zentra Monitor..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 monitor.py

echo "Premi INVIO per uscire..."
read
