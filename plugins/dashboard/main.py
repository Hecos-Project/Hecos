"""
MODULO: Dashboard - Zentra Core v0.8
DESCRIZIONE: Monitoraggio hardware (CPU, RAM, GPU/VRAM) e stato backend AI (Ollama/Kobold).
Fornisce anche comandi vocali/testuali per interrogare le risorse di sistema.
"""
import sys
import psutil
import threading
import time
import requests
import json

from core.logging import logger
from core.i18n import translator
from app.config import ConfigManager

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    logger.errore("DASHBOARD: GPUtil not installed. VRAM and GPU not available.")

_backend_status = "STARTING"
_lock = threading.Lock()

def _monitora_backend():
    """Thread che monitora periodicamente lo stato del backend AI."""
    global _backend_status
    cfg_mgr = ConfigManager()
    monitor_interval = cfg_mgr.get_plugin_config("DASHBOARD", "monitor_interval", 2)
    backend_timeout = cfg_mgr.get_plugin_config("DASHBOARD", "backend_timeout", 0.5)

    while True:
        try:
            config = cfg_mgr.config
            backend_type = config.get('backend', {}).get('tipo', 'ollama')
            backend_cfg = config.get('backend', {}).get(backend_type, {})

            if backend_type == 'cloud':
                _backend_status = "CLOUD"
            elif backend_type == 'kobold':
                url = backend_cfg.get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
                r = requests.get(url, timeout=backend_timeout)
                _backend_status = "READY" if r.status_code == 200 else "ERROR"
            else:
                r = requests.get("http://localhost:11434/api/tags", timeout=backend_timeout)
                _backend_status = "READY" if r.status_code == 200 else "ERROR OLLAMA"

        except requests.exceptions.ConnectionError:
            _backend_status = "OFFLINE"
        except requests.exceptions.Timeout:
            _backend_status = "TIMEOUT"
        except json.JSONDecodeError:
            _backend_status = "ERROR CONFIG"
        except Exception as e:
            logger.errore(f"DASHBOARD: Backend monitor error: {e}")
            _backend_status = "ERROR"

        time.sleep(monitor_interval)

def avvia_monitoraggio_backend():
    """Avvia il thread di monitoraggio del backend."""
    thread = threading.Thread(target=_monitora_backend, daemon=True)
    thread.start()
    logger.info("DASHBOARD: Backend monitor started.")

def get_backend_status():
    """Restituisce lo stato corrente del backend AI."""
    with _lock:
        return _backend_status

def get_stats():
    """Recupera le statistiche hardware (CPU, RAM, GPU/VRAM)."""
    stats = {
        "cpu": 0,
        "ram": 0,
        "vram": "N/A",
        "gpu_load": "N/A",
        "stato_gpu": "N/A",
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
                    stats["stato_gpu"] = "WAITING" if vram_percent > 80 else "READY"
                else:
                    stats["vram"] = "N/A (No GPU)"
                    stats["gpu_load"] = "N/A"
                    stats["stato_gpu"] = "N/A"
            except Exception as e:
                logger.errore(f"DASHBOARD: GPU read error: {e}")
                stats["vram"] = "ERR"
                stats["gpu_load"] = "ERR"
                stats["stato_gpu"] = "ERR"
        else:
            stats["vram"] = "N/A (Missing GPUtil)"
            stats["gpu_load"] = "N/A"
            stats["stato_gpu"] = "N/A"

    except Exception as e:
        logger.errore(f"DASHBOARD: Critical get_stats error: {e}")

    return stats

def info():
    """Manifest del plugin per il registro centrale."""
    return {
        "tag": "DASHBOARD",
        "desc": translator.t("plugin_dashboard_desc"),
        "comandi": {
            "resources": translator.t("plugin_dashboard_risorse_desc"),
            "vram": translator.t("plugin_dashboard_vram_desc"),
            "status": translator.t("plugin_dashboard_stato_desc"),
            "all": translator.t("plugin_dashboard_tutto_desc")
        },
        "esempio": "[DASHBOARD: resources] or [DASHBOARD: all]"
    }

def status():
    """Stato del plugin."""
    return translator.t("plugin_dashboard_status_online")

def config_schema():
    """
    Schema di configurazione per questo plugin.
    """
    return {
        "monitor_interval": {
            "type": "int",
            "default": 2,
            "min": 1,
            "max": 10,
            "description": translator.t("plugin_dashboard_monitor_interval_desc")
        },
        "backend_timeout": {
            "type": "float",
            "default": 0.5,
            "min": 0.1,
            "max": 5.0,
            "description": translator.t("plugin_dashboard_timeout_desc")
        }
    }

def esegui(comando):
    """Esegue i comandi del plugin."""
    stats = get_stats()
    cmd = comando.lower().strip()

    if cmd == "resources" or cmd == "risorse":
        return translator.t("plugin_dashboard_stats_cpu_ram", cpu=stats['cpu'], ram=stats['ram'])
    elif cmd == "vram":
        return translator.t("plugin_dashboard_stats_vram_gpu", vram=stats['vram'], load=stats['gpu_load'])
    elif cmd == "status" or cmd == "stato":
        return translator.t("plugin_dashboard_stats_backend", status=stats['backend_status'])
    elif cmd == "all" or cmd == "tutto" or cmd == "":
        if stats['vram'] in ("N/D", "N/A", "ERR", "N/A (Missing GPUtil)", "N/A (No GPU)"):
            return translator.t("plugin_dashboard_stats_full", cpu=stats['cpu'], ram=stats['ram'], gpu_status=stats['stato_gpu'], backend_status=stats['backend_status'])
        else:
            return translator.t("plugin_dashboard_stats_full_gpu", cpu=stats['cpu'], ram=stats['ram'], vram=stats['vram'], load=stats['gpu_load'], backend_status=stats['backend_status'])
    else:
        # Default fallback same as 'tutto'
        if stats['vram'] in ("N/D", "N/A", "ERR", "N/A (Missing GPUtil)", "N/A (No GPU)"):
            return translator.t("plugin_dashboard_stats_full", cpu=stats['cpu'], ram=stats['ram'], gpu_status=stats['stato_gpu'], backend_status=stats['backend_status'])
        else:
            return translator.t("plugin_dashboard_stats_full_gpu", cpu=stats['cpu'], ram=stats['ram'], vram=stats['vram'], load=stats['gpu_load'], backend_status=stats['backend_status'])