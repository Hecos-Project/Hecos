"""
Plugin: Remote Triggers
VERSION: 1.0.0
DESCRIPTION: Attiva il PTT (Push-To-Talk) tramite input remoti:
             - Webhook HTTP (bottoni USB, Arduino, ESP32)
             - MediaSession API / tasti hardware (cuffie Bluetooth, iPhone)

Il plugin si registra su Flask e inietta il JS nella WebUI.
Se disabilitato, non produce errori: le rotte non vengono registrate,
il JS non viene iniettato.
"""

try:
    from zentra.core.logging import logger
except ImportError:
    class _DL:
        def info(self, *a, **k): print("[RT]", *a)
        def debug(self, *a, **k): pass
        def warning(self, *a, **k): print("[RT WARN]", *a)
        def error(self, *a, **k): print("[RT ERR]", *a)
    logger = _DL()


class RemoteTriggerPlugin:
    """
    Zentra Remote Triggers — Plugin Interface.
    Espone le funzionalità al Core senza necessità di tool LLM.
    """

    def __init__(self):
        self.tag = "REMOTE_TRIGGERS"
        self.desc = "Attivazione PTT da periferiche hardware e dispositivi remoti"
        self.status = "online"

    def info(self):
        return {"tag": self.tag, "desc": self.desc}


# Istanza singleton del plugin
tools = RemoteTriggerPlugin()


def info():
    return tools.info()


def status():
    return tools.status


def init_routes(app):
    """
    Registra le route Flask per i webhook e la pagina di status.
    Chiamato da routes.py del web_ui quando il plugin è attivo.
    """
    from .routes import init_remote_triggers_routes
    init_remote_triggers_routes(app, logger)
    logger.info("[RemoteTriggers] Routes registered.")
