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

import sys
_server_lock = threading.Lock()

def set_state_manager(sm) -> None:
    """Inject the live StateManager so audio-toggle routes can use it."""
    # We use sys to share the state manager because this module is often double-imported
    # (once as __main__ and once as plugins.web_ui.server).
    sys.zentra_state_manager = sm


def get_state_manager():
    """Returns current state_manager (may be None before injection)."""
    return getattr(sys, "zentra_state_manager", None)


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

        # --- ZENTRA AUTH SYSTEM ---
        app.secret_key = self.config_manager.config.get("system", {}).get("flask_secret_key", "zentra_default_secret_key_84nd")
        
        from flask_login import LoginManager, current_user
        from core.auth.auth_manager import auth_mgr
        
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = "login_page"

        @login_manager.user_loader
        def load_user(user_id):
            return auth_mgr.get_user_by_id(user_id)

        from flask import request, redirect, url_for, jsonify
        @app.before_request
        def require_login():
            # Exempt routes for the login process and static files
            exempt_paths = ['/login', '/logout', '/static']
            if any(request.path.startswith(p) for p in exempt_paths):
                return
            
            if not current_user.is_authenticated:
                if request.path.startswith('/api/') or request.path.startswith('/zentra/api/'):
                    return jsonify({"ok": False, "error": "Authentication required. Please login."}), 401
                return redirect(url_for('login_page'))
        # --------------------------

        # Get debug state from system config
        debug_on = self.config_manager.config.get("system", {}).get("flask_debug", False)

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

        # Register all routes — pass getter so routes always read the current SM
        init_routes(app, self.config_manager, self.root_dir, self.logger, get_state_manager)
        init_chat_routes(app, self.config_manager, self.root_dir, self.logger)
        from .routes_auth import init_auth_routes
        init_auth_routes(app, self.logger)

        def _run():
            try:
                # SSL Setup
                ssl_context = None
                webui_cfg = self.config_manager.config.get("plugins", {}).get("WEB_UI", {})
                use_https = webui_cfg.get("https_enabled", False)
                scheme = "https" if use_https else "http"

                if use_https:
                    from .ssl_manager import ensure_certificates
                    cert_file = webui_cfg.get("cert_file", "certs/cert.pem")
                    key_file = webui_cfg.get("key_file", "certs/key.pem")
                    ssl_paths = ensure_certificates(cert_file, key_file)
                    
                    if ssl_paths:
                        ssl_context = ssl_paths  # Flask expects a tuple (cert, key)
                    else:
                        self.logger.warning("[WebUI] HTTPS requested but cert generation failed. Falling back to HTTP.")
                        scheme = "http"

                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(('10.254.254.254', 1))
                    lan_ip = s.getsockname()[0]
                    s.close()
                except Exception:
                    lan_ip = "127.0.0.1"

                self.logger.info(
                    f"[WebUI] 🚀 Server live (debug={debug_on}) → "
                    f"{scheme}://{lan_ip}:{self.port}/chat  |  "
                    f"{scheme}://{lan_ip}:{self.port}/zentra/config/ui"
                )
                # We disable reloader to avoid starting Zentra threads twice
                # Bind to 0.0.0.0 to handle localhost/127.0.0.1/::1 issues on Windows
                if ssl_context:
                    app.run(host="0.0.0.0", port=self.port, debug=debug_on, use_reloader=False, ssl_context=ssl_context)
                else:
                    app.run(host="0.0.0.0", port=self.port, debug=debug_on, use_reloader=False)
            except Exception as e:
                self.logger.error(f"[WebUI] Flask exception: {e}")

        self._thread = threading.Thread(target=_run, daemon=True, name="ZentraWebUIThread")
        self._thread.start()


def start_if_needed(config_manager, root_dir: str, port: int = 7070) -> None:
    """Singleton entry point — safe to call multiple times, even with two module instances."""
    # We use sys to share the singleton because this module is often double-imported
    # (once as __main__ and once as plugins.web_ui.server).
    import sys
    
    # We also need a shared lock
    if not hasattr(sys, "_zentra_webui_lock"):
        import threading
        sys._zentra_webui_lock = threading.Lock()
    
    with sys._zentra_webui_lock:
        b_log = logging.getLogger("ZentraWebUI")
        try:
            srv = getattr(sys, "_zentra_webui_instance", None)
            
            alive = (srv is not None
                     and srv._thread is not None
                     and srv._thread.is_alive())
            
            if not alive:
                b_log.info(f"[WebUI] Starting server on port {port}...")
                srv = ZentraWebUIServer(config_manager, root_dir, port, logger=b_log)
                srv.start()
                setattr(sys, "_zentra_webui_instance", srv)
            else:
                # Already running
                pass
        except Exception as e:
            b_log.error(f"[WebUI] Startup error: {e}")


# ── Standalone (.bat launcher) ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()
    
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
    
    # Initialize basic logging (disable external windows for webui standalone)
    logger.init_logger(cfg.config, allow_external_windows=False)
    
    # Initialize translator with current config language
    init_translator(cfg.config.get("language", "en"))

    # Initialize memory vault (creates DB if not present)
    from memory.brain_interface import initialize_vault, maybe_clear_on_restart
    initialize_vault()
    maybe_clear_on_restart(cfg.config)
    
    # Initialize plugin registry (needed for plugin execution from WebUI process)
    from core.system import plugin_loader
    plugin_loader.update_capability_registry(cfg.config)

    # Initialize state manager with config_audio.json settings
    from core.audio.device_manager import get_audio_config
    acfg = get_audio_config()
    
    sm = StateManager(
        initial_voice_status=acfg.get('voice_status', True),
        initial_listening_status=acfg.get('listening_status', True),
        initial_audio_mode=acfg.get('audio_mode', 'auto')
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

    def standalone_voice_poller():
        """Polls for detected voice commands in standalone mode and pushes them to WebUI clients."""
        while True:
            if sm and sm.detected_voice_command:
                cmd = sm.detected_voice_command
                sm.detected_voice_command = None
                logger.info(f"[WEB] Dispatched standalone voice command: '{cmd}'")
                sm.add_event("voice_detected", {"text": cmd, "standalone": True})
            import time
            time.sleep(0.2)

    import threading
    threading.Thread(target=standalone_voice_poller, daemon=True).start()

    def is_webui_already_open(root_dir):
        """Check if a WebUI tab is already active via heartbeat file."""
        import time, json, os
        hb_file = os.path.join(root_dir, "logs", "webui_heartbeat.json")
        if not os.path.exists(hb_file): 
            return False
        try:
            with open(hb_file, "r") as f:
                data = json.load(f)
                # If any page (chat or config) checked in last 15 seconds, assume open
                now = time.time()
                for ts in data.values():
                    if now - ts < 15: return True
        except: pass
        return False

    # Auto-open browser in standalone mode ONLY if not already open
    def _delayed_browser():
        import time
        import webbrowser
        time.sleep(1.5)
        if not is_webui_already_open(root):
            webui_cfg = cfg.config.get("plugins", {}).get("WEB_UI", {})
            scheme = "https" if webui_cfg.get("https_enabled", False) else "http"
            webbrowser.open(f"{scheme}://127.0.0.1:7070/chat")
        else:
            print("[WEB] WebUI already active in a tab (heartbeat detected). Skipping auto-open.")
    
    import threading
    threading.Thread(target=_delayed_browser, daemon=True).start()

    start_if_needed(cfg, root, port=7070)

    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Zentra WebUI server stopped.")
