"""
zentra_bridge/webui/web_config/__init__.py
Compatibility shim — all logic has moved to plugins/web_ui/.
This shim re-exports start_if_needed so that legacy bridge code continues working.
"""
try:
    from plugins.web_ui.server import start_if_needed, ZentraWebUIServer as ZentraConfigServer
except ImportError:
    # Graceful fallback if plugin not yet loaded (e.g. standalone bridge testing)
    def start_if_needed(*args, **kwargs):
        import logging
        logging.getLogger("WebUI_Bridge").warning(
            "[WebUI] Plugin plugins/web_ui not found — server not started."
        )
    ZentraConfigServer = None

__all__ = ["start_if_needed", "ZentraConfigServer"]
