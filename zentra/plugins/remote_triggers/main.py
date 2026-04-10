"""
Plugin: Remote Triggers
VERSION: 1.0.0
DESCRIPTION: Activates PTT (Push-To-Talk) via remote inputs:
             - HTTP Webhooks (USB buttons, Arduino, ESP32)
             - MediaSession API / Hardware keys (Bluetooth headphones, iPhone)

The plugin registers with Flask and injects JS into the WebUI.
If disabled, it produces no errors: routes are not registered, 
and JS is not injected.
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
    Exposes functionality to the Core without requiring LLM tools.
    """

    def __init__(self):
        self.tag = "REMOTE_TRIGGERS"
        self.desc = "PTT activation from hardware devices and remote clients"
        self.status = "online"

    def info(self):
        return {"tag": self.tag, "desc": self.desc}


# Singleton instance of the plugin
tools = RemoteTriggerPlugin()


def info():
    return tools.info()


def status():
    return tools.status


def init_routes(app):
    """
    Registers Flask routes for webhooks and status page.
    Called by web_ui routes.py when the plugin is active.
    """
    from .routes import init_remote_triggers_routes
    init_remote_triggers_routes(app, logger)
    logger.info("[RemoteTriggers] Routes registered.")
