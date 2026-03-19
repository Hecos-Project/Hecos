@echo off
title Avvio Ollama con Accelerazione GPU (Vulkan)
cd /d "C:\AuraCore"

echo Impostazione variabili d'ambiente...
set OLLAMA_VULKAN=1
set OLLAMA_GPU_OVERHEAD=0
set OLLAMA_NUM_PARALLEL=1

echo Avvio del server Ollama...
start /min "" "C:\Users\Asus\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 8

echo Avvio di Aura...
python main.py
pause