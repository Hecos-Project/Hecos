@echo off
title ZENTRA CORE - Backend VULKAN (Nvidia 920MX)

cd /d "%~dp0"

echo ======================================================
echo    ATTIVAZIONE VULKAN - NVIDIA 920MX (Ollama 0.18.0)
echo ======================================================

:: --- VARIABILE CRITICA: SBLOCCO VULKAN ---
:: Senza questa, Ollama 0.18+ ignora la GPU
set OLLAMA_VULKAN=1

:: Forza l'uso della libreria Vulkan
set OLLAMA_LLM_LIBRARY=vulkan

:: --- OTTIMIZZAZIONE VRAM (2GB) ---
:: Impedisce crash da saturazione memoria
set OLLAMA_GPU_OVERHEAD=1
:: Disabilita caricamenti paralleli per non dividere la VRAM
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_KEEP_ALIVE=-1

:: --- VARIABILI ZENTRA ---
setx GROQ_API_KEY "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" >nul

echo [1/3] Pulizia processi precedenti...
taskkill /f /im ollama.exe >nul 2>&1

echo [2/3] Avvio server Ollama...
:: Usiamo 'start' cosi' vedi i log in una finestra a parte
start "LOGS OLLAMA" cmd /c "ollama serve"

echo [3/3] Attesa inizializzazione Driver Vulkan (12 secondi)...
timeout /t 12 /nobreak

echo Lancio Zentra Monitor...
python monitor.py

pause