"""
MODULO: Dashboard - Aura Core v0.7
DESCRIZIONE: Monitoraggio hardware (CPU, RAM, GPU/VRAM) e stato backend AI (Ollama/Kobold).
Fornisce anche comandi vocali/testuali per interrogare le risorse di sistema.
"""
import sys
import psutil
import threading
import time
import requests
import json

from core import logger

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    logger.errore("DASHBOARD: GPUtil non installato. VRAM e GPU non disponibili.")

_backend_status = "AVVIO"
_lock = threading.Lock()

def _monitora_backend():
    global _backend_status
    while True:
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            backend_type = config.get('backend', {}).get('tipo', 'ollama')
            backend_cfg = config.get('backend', {}).get(backend_type, {})

            if backend_type == 'kobold':
                url = backend_cfg.get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
                r = requests.get(url, timeout=0.5)
                _backend_status = "PRONTA" if r.status_code == 200 else "ERRORE"
            else:
                r = requests.get("http://localhost:11434/api/tags", timeout=0.5)
                _backend_status = "PRONTA" if r.status_code == 200 else "ERRORE OLLAMA"
                
        except requests.exceptions.ConnectionError:
            _backend_status = "OFFLINE"
        except requests.exceptions.Timeout:
            _backend_status = "TIMEOUT"
        except json.JSONDecodeError:
            _backend_status = "ERRORE CONFIG"
        except Exception as e:
            logger.errore(f"DASHBOARD: Errore monitoraggio backend: {e}")
            _backend_status = "ERRORE"
            
        time.sleep(2)

def avvia_monitoraggio_backend():
    thread = threading.Thread(target=_monitora_backend, daemon=True)
    thread.start()
    logger.info("DASHBOARD: Monitoraggio backend avviato.")

def get_backend_status():
    with _lock:
        return _backend_status

def get_stats():
    stats = {
        "cpu": 0,
        "ram": 0,
        "vram": "N/D",
        "gpu_load": "N/D",
        "stato_gpu": "N/D",
        "backend_status": get_backend_status()
    }
    
    try:
        stats["cpu"] = psutil.cpu_percent(interval=0.1)
        stats["ram"] = psutil.virtual_memory().percent
        
        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    vram_percent = (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal > 0 else 0
                    vram_usata = f"{int(vram_percent)}% ({int(gpu.memoryUsed)}MB/{int(gpu.memoryTotal)}MB)"
                    gpu_load = f"{int(gpu.load * 100)}%"
                    
                    stats["vram"] = vram_usata
                    stats["gpu_load"] = gpu_load
                    stats["stato_gpu"] = "ATTENDERE" if vram_percent > 80 else "PRONTA"
                else:
                    stats["vram"] = "N/A (No GPU)"
                    stats["gpu_load"] = "N/A"
                    stats["stato_gpu"] = "N/A"
            except Exception as e:
                logger.errore(f"DASHBOARD: Errore lettura GPU: {e}")
                stats["vram"] = "ERR"
                stats["gpu_load"] = "ERR"
                stats["stato_gpu"] = "ERR"
        else:
            stats["vram"] = "N/A (GPUtil mancante)"
            stats["gpu_load"] = "N/A"
            stats["stato_gpu"] = "N/A"
            
    except Exception as e:
        logger.errore(f"DASHBOARD: Errore critico get_stats: {e}")
        
    return stats

def info():
    return {
        "tag": "DASHBOARD",
        "desc": "Monitoraggio hardware e stato backend AI.",
        "comandi": {
            "risorse": "Mostra CPU e RAM.",
            "vram": "Mostra dettagli VRAM e carico GPU.",
            "stato": "Mostra stato del backend (Ollama/Kobold).",
            "tutto": "Mostra tutte le informazioni disponibili."
        }
    }

def status():
    return "ONLINE (Telemetria attiva)"

def esegui(comando):
    stats = get_stats()
    cmd = comando.lower().strip()
    
    if cmd == "risorse":
        return f"CPU: {stats['cpu']}%, RAM: {stats['ram']}%."
    elif cmd == "vram":
        if stats['vram'] in ("N/D", "N/A", "ERR"):
            return f"VRAM: {stats['vram']}, Carico GPU: {stats['gpu_load']}."
        else:
            return f"VRAM: {stats['vram']}, Carico GPU: {stats['gpu_load']}."
    elif cmd == "stato":
        return f"Backend AI: {stats['backend_status']}."
    elif cmd == "tutto" or cmd == "":
        if stats['vram'] in ("N/D", "N/A", "ERR"):
            return (f"CPU: {stats['cpu']}%, RAM: {stats['ram']}%, "
                    f"Stato GPU: {stats['stato_gpu']}, "
                    f"Backend: {stats['backend_status']}.")
        else:
            return (f"CPU: {stats['cpu']}%, RAM: {stats['ram']}%, "
                    f"VRAM: {stats['vram']}, GPU Load: {stats['gpu_load']}, "
                    f"Backend: {stats['backend_status']}.")
    else:
        if stats['vram'] in ("N/D", "N/A", "ERR"):
            return (f"CPU: {stats['cpu']}%, RAM: {stats['ram']}%, "
                    f"Stato GPU: {stats['stato_gpu']}, "
                    f"Backend: {stats['backend_status']}.")
        else:
            return (f"CPU: {stats['cpu']}%, RAM: {stats['ram']}%, "
                    f"VRAM: {stats['vram']}, GPU Load: {stats['gpu_load']}, "
                    f"Backend: {stats['backend_status']}.")