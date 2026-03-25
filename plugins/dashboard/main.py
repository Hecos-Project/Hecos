"""
Plugin: Dashboard
Monitoraggio hardware (CPU, RAM, GPU/VRAM) e stato backend AI (Ollama/Kobold).
"""
import sys
import psutil
import threading
import time
import requests
import json
try:
    from core.logging import logger
    from core.i18n import translator
    from app.config import ConfigManager
except ImportError:
    class DummyLogger:
        def debug(self, *args, **kwargs): print("[DSB_DEBUG]", *args)
        def info(self, *args, **kwargs): print("[DSB_INFO]", *args)
        def warning(self, *args, **kwargs): print("[DSB_WARN]", *args)
        def errore(self, *args, **kwargs): print("[DSB_ERR]", *args)
    logger = DummyLogger()
    class DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = DummyTranslator()
    class DummyConfigMgr:
        def __init__(self): self.config = {}
        def get_plugin_config(self, tag, key, default): return default
    ConfigManager = DummyConfigMgr

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    logger.errore("DASHBOARD: GPUtil not installed. VRAM and GPU not available.")

# Variabili globali per lo stato condiviso tra thread e classe
_backend_status = "STARTING"
_monitor_thread_started = False
_lock = threading.Lock()

def _monitora_backend():
    """Thread che monitora periodicamente lo stato del backend AI."""
    global _backend_status
    cfg_mgr = ConfigManager()
    
    while True:
        try:
            # Ricarichiamo il config ad ogni ciclo per recepire modifiche fatte con F7
            cfg_mgr.reload()
            
            # Ricarica l'intervallo ogni volta per dinamicità
            monitor_interval = cfg_mgr.get_plugin_config("DASHBOARD", "monitor_interval", 2)
            backend_timeout = cfg_mgr.get_plugin_config("DASHBOARD", "backend_timeout", 0.5)
            
            config = cfg_mgr.config
            backend_type = config.get('backend', {}).get('tipo', 'ollama')
            backend_cfg = config.get('backend', {}).get(backend_type, {})

            if backend_type == 'cloud':
                status_val = "CLOUD"
            elif backend_type == 'kobold':
                url = backend_cfg.get('url', 'http://localhost:5001').rstrip('/') + '/api/v1/model'
                r = requests.get(url, timeout=backend_timeout)
                status_val = "READY" if r.status_code == 200 else "ERROR"
            else:
                r = requests.get("http://localhost:11434/api/tags", timeout=backend_timeout)
                status_val = "READY" if r.status_code == 200 else "ERROR OLLAMA"

            with _lock:
                _backend_status = status_val

        except requests.exceptions.ConnectionError:
            with _lock: _backend_status = "OFFLINE"
        except requests.exceptions.Timeout:
            with _lock: _backend_status = "TIMEOUT"
        except Exception as e:
            logger.debug("DASHBOARD", f"Backend monitor update error: {e}")
            with _lock: _backend_status = "ERROR"

        time.sleep(monitor_interval)

class DashboardTools:
    """
    Plugin: Dashboard & Hardware Monitor
    Fornisce statistiche in tempo reale su CPU, RAM, VRAM e stato del backend AI.
    """

    def __init__(self):
        self.tag = "DASHBOARD"
        self.desc = translator.t("plugin_dashboard_desc")
        
        self.config_schema = {
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
        
        # Avvia il monitoraggio in background se non è già attivo
        self._avvia_monitoraggio()

    @property
    def status(self):
        return translator.t("plugin_dashboard_status_online")

    def _avvia_monitoraggio(self):
        global _monitor_thread_started
        if not _monitor_thread_started:
            thread = threading.Thread(target=_monitora_backend, daemon=True)
            thread.start()
            _monitor_thread_started = True
            logger.info("DASHBOARD: Backend monitor thread initialized via class.")

    def get_system_resources(self) -> str:
        """
        Restituisce un riepilogo dell'uso di CPU e RAM di sistema.
        """
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        return translator.t("plugin_dashboard_stats_cpu_ram", cpu=cpu, ram=ram)

    def get_gpu_status(self) -> str:
        """
        Restituisce lo stato della scheda video (GPU), inclusa la VRAM usata e il carico termico/computazionale.
        """
        if not GPUTIL_AVAILABLE:
            return "Modulo GPUtil non installato. Impossibile leggere dati GPU."
        
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return "Nessuna GPU dedicata rilevata."
            
            # Su portatili Dual-GPU (es. Intel + Nvidia), seleziona la GPU discreta
            # ordinando per VRAM totale decrescente in modo da ignorare l'integrata
            gpus.sort(key=lambda x: x.memoryTotal, reverse=True)
            gpu = gpus[0]
            
            vram_percent = (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal > 0 else 0
            vram_usata = f"{int(vram_percent)}% ({int(gpu.memoryUsed)}MB/{int(gpu.memoryTotal)}MB)"
            gpu_load = f"{int(gpu.load * 100)}%"
            
            return translator.t("plugin_dashboard_stats_vram_gpu", vram=vram_usata, load=gpu_load)
        except Exception as e:
            return f"Errore lettura GPU: {e}"

    def _get_raw_backend_status(self) -> str:
        """Restituisce il codice grezzo di stato del backend (es. 'CLOUD', 'READY', 'ERROR')."""
        with _lock:
            return _backend_status

    def get_backend_status(self) -> str:
        """
        Verifica se il backend di Intelligenza Artificiale (Ollama, Kobold o Cloud) è online e pronto.
        """
        stato = self._get_raw_backend_status()
        return translator.t("plugin_dashboard_stats_backend", status=stato)

    def get_full_dashboard(self) -> str:
        """
        Restituisce un report completo di tutte le risorse hardware e dello stato del backend AI.
        Usa questo strumento se l'utente chiede 'come stai' o 'fammi un report del sistema'.
        """
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        
        with _lock:
            b_status = _backend_status

        vram_info = "N/A"
        gpu_load = "N/A"
        stato_gpu = "N/A"

        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    vram_p = (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal > 0 else 0
                    vram_info = f"{int(vram_p)}% ({int(gpu.memoryUsed)}MB/{int(gpu.memoryTotal)}MB)"
                    gpu_load = f"{int(gpu.load * 100)}%"
                    stato_gpu = "WAITING" if vram_p > 80 else "READY"
            except: pass

        if vram_info in ("N/D", "N/A", "N/A (No GPU)"):
            return translator.t("plugin_dashboard_stats_full", cpu=cpu, ram=ram, gpu_status=stato_gpu, backend_status=b_status)
        else:
            return translator.t("plugin_dashboard_stats_full_gpu", cpu=cpu, ram=ram, vram=vram_info, load=gpu_load, backend_status=b_status)

# Istanzia pubblicamente lo strumento per l'esportazione verso il Core
tools = DashboardTools()

# --- COMPATIBILITY SHIMS (Legacy call support) ---
def get_stats():
    """Wrapper per compatibilità con interface.py e ui_updater.py"""
    # Usiamo un dizionario compatibile con il vecchio formato atteso
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    
    with _lock:
        b_status = _backend_status

    vram_info = "N/A"
    gpu_load = "N/A"
    stato_gpu = "N/A"

    if GPUTIL_AVAILABLE:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                vram_p = (gpu.memoryUsed / gpu.memoryTotal) * 100 if gpu.memoryTotal > 0 else 0
                vram_info = f"{int(vram_p)}% ({int(gpu.memoryUsed)}MB/{int(gpu.memoryTotal)}MB)"
                gpu_load = f"{int(gpu.load * 100)}%"
                stato_gpu = "WAITING" if vram_p > 80 else "READY"
        except: pass

    return {
        "cpu": cpu,
        "ram": ram,
        "vram": vram_info,
        "gpu_load": gpu_load,
        "stato_gpu": stato_gpu,
        "backend_status": b_status
    }

def avvia_monitoraggio_backend():
    """Wrapper per compatibilità con application.py"""
    tools._avvia_monitoraggio()

def get_backend_status():
    """Wrapper per compatibilità con input_handler.py - restituisce il codice grezzo (es. 'CLOUD', 'READY')."""
    return tools._get_raw_backend_status()

def esegui(comando):
    """Wrapper per compatibilità con plugin legacy e vecchio processore"""
    stats = get_stats()
    cmd = comando.lower().strip()
    if cmd in ["resources", "risorse"]:
        return tools.get_system_resources()
    elif cmd == "vram":
        return tools.get_gpu_status()
    elif cmd in ["status", "stato"]:
        return tools.get_backend_status()
    else:
        return tools.get_full_dashboard()

def info():
    """Manifest legacy per il registro centrale"""
    return {
        "tag": "DASHBOARD",
        "desc": tools.desc,
        "comandi": {
            "resources": "Info CPU/RAM",
            "vram": "Info GPU",
            "status": "Stato Backend",
            "all": "Report completo"
        }
    }