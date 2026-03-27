"""
WEB_UI Plugin — Server
Flask daemon thread that serves both the Config Panel and the native Chat UI.
"""
import threading
import logging
import os
from .routes import init_routes
from .routes_chat import init_chat_routes

log = logging.getLogger("ZentraWebUIServer")

from app.state_manager import StateManager
from app.threads import AscoltoThread

_global_server_instance = None
_server_lock = threading.Lock()
_state_manager = None   # Injected by application.py after startup


def set_state_manager(sm) -> None:
    """Inject the live StateManager so audio-toggle routes can use it."""
    global _state_manager
    _state_manager = sm


def get_state_manager():
    """Returns current state_manager (may be None before injection)."""
    return _state_manager


class ZentraWebUIServer:
    def __init__(self, config_manager, root_dir: str, port: int, logger=None):
        self.config_manager = config_manager
        self.root_dir = root_dir
        self.port = port
        self.logger = logger or log
        self._thread = None

    def start(self) -> None:
        try:
            from flask import Flask
        except ImportError as e:
            self.logger.warning(f"[WebUI] Flask not available ({e})")
            return

        from core.i18n.translator import t

        # Templates are inside this plugin's own templates/ folder
        tpl_dir = os.path.join(os.path.dirname(__file__), "templates")
        app = Flask("ZentraWebUI", template_folder=tpl_dir)
        
        # Inject translation system into Jinja2 templates
        app.jinja_env.globals.update(t=t)

        # Get debug state from system config
        debug_on = self.config_manager.config.get("system", {}).get("flask_debug", False)

        # Silence werkzeug noise ONLY if debug is off
        import logging as _lg
        wz_log = _lg.getLogger("werkzeug")
        if not debug_on:
            try:
                wz_log.setLevel(_lg.ERROR)
                app.logger.disabled = True
            except Exception:
                pass
        else:
            # When debug is ON, ensure logs propagate to Zentra's root logger
            wz_log.setLevel(_lg.INFO)
            wz_log.propagate = True
            _chat_log.info("[WebUI] Flask/Werkzeug logging enabled.")

        # Register all routes — pass getter so routes always read the current SM
        init_routes(app, self.config_manager, self.root_dir, self.logger, get_state_manager)
        init_chat_routes(app, self.config_manager, self.root_dir, self.logger)

        def _run():
            try:
                self.logger.info(
                    f"[WebUI] 🚀 Server live (debug={debug_on}) → "
                    f"http://127.0.0.1:{self.port}/chat  |  "
                    f"http://127.0.0.1:{self.port}/zentra/config/ui"
                )
                # We disable reloader to avoid starting Zentra threads twice
                app.run(host="127.0.0.1", port=self.port, debug=debug_on, use_reloader=False)
            except Exception as e:
                self.logger.error(f"[WebUI] Flask exception: {e}")

        self._thread = threading.Thread(target=_run, daemon=True, name="ZentraWebUIThread")
        self._thread.start()


def start_if_needed(config_manager, root_dir: str, port: int = 7070) -> None:
    """Singleton entry point — safe to call multiple times."""
    global _global_server_instance
    with _server_lock:
        b_log = logging.getLogger("ZentraWebUI")
        try:
            alive = (_global_server_instance is not None
                     and _global_server_instance._thread is not None
                     and _global_server_instance._thread.is_alive())
            if not alive:
                b_log.info(f"[WebUI] Starting server on port {port}.")
                srv = ZentraWebUIServer(config_manager, root_dir, port, logger=b_log)
                srv.start()
                _global_server_instance = srv
        except Exception as e:
            b_log.error(f"[WebUI] Startup error: {e}")


# ── Standalone (.bat launcher) ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(root)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    from app.config import ConfigManager
    from core.i18n.translator import init_translator
    from core.logging import logger
    cfg = ConfigManager()
    
    # Initialize basic logging
    logger.init_logger(cfg.config)
    
    # Initialize translator with current config language
    init_translator(cfg.config.get("language", "en"))

    # Initialize state manager with config_audio.json settings
    from core.audio.device_manager import get_audio_config
    acfg = get_audio_config()
    
    sm = StateManager(
        initial_voice_status=acfg.get('voice_status', True),
        initial_listening_status=acfg.get('listening_status', True),
        initial_audio_mode=cfg.get('audio_mode', default='auto')
    )
    sm.push_to_talk    = acfg.get('push_to_talk', False)
    sm.ptt_hotkey      = acfg.get('ptt_hotkey', 'ctrl+shift')
    sm.stt_source      = acfg.get('stt_source', 'system')
    sm.tts_destination = acfg.get('tts_destination', 'web')
    set_state_manager(sm)

    # Start the listening thread (Whisper + PTT)
    logger.info("[WEB] Starting standalone audio engine...")
    audio_th = AscoltoThread(sm)
    audio_th.start()

    # Auto-open browser in standalone mode
    def _delayed_browser():
        import time
        import webbrowser
        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:7070/chat")
    
    import threading
    threading.Thread(target=_delayed_browser, daemon=True).start()

    start_if_needed(cfg, root, port=7070)

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Zentra WebUI server stopped.")
