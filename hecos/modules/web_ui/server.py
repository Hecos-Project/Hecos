"""
WEB_UI Plugin — Server
Flask daemon thread that serves both the Config Panel and the native Chat UI.
"""
import sys
import os
import threading
import logging
from flask import Flask, send_from_directory, request, redirect, url_for, jsonify
from flask_login import LoginManager, current_user
from .routes import init_routes

log = logging.getLogger("HecosWebUIServer")

from hecos.app.state_manager import StateManager
from hecos.app.threads import AscoltoThread

import sys
_server_lock = threading.Lock()

def set_state_manager(sm) -> None:
    """Inject the live StateManager so audio-toggle routes can use it."""
    # We use sys to share the state manager because this module is often double-imported
    # (once as __main__ and once as modules.web_ui.server).
    sys.hecos_state_manager = sm


def get_state_manager():
    """Returns current state_manager (may be None before injection)."""
    return getattr(sys, "hecos_state_manager", None)


class HecosWebUIServer:
    def __init__(self, config_manager, root_dir: str, port: int, logger=None):
        self.config_manager = config_manager
        if self.config_manager is None:
            class DummyConfig:
                config = {"plugins": {"WEB_UI": {"https_enabled": True, "port": 7070}}}
            self.config_manager = DummyConfig()
            
        self.root_dir = root_dir
        self.port = port
        self.logger = logger or logging.getLogger()
        self._thread = None

    def start(self) -> None:
        try:
            from .server_flask import create_flask_app
            app, debug_on = create_flask_app(
                self.config_manager, 
                self.root_dir, 
                self.logger, 
                get_state_manager
            )
        except Exception as e:
            import traceback
            print(f"[DEBUG BOOT] CRITICAL ERROR during flask creation: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            return

        # Start PTT Bus
        try:
            from hecos.core.audio import ptt_bus
            ptt_bus.start(state=get_state_manager())
            self.logger.info("[WebUI] PTT Bus started.")
        except Exception as e:
            self.logger.warning(f"[WebUI] PTT Bus could not start: {e}")

        # Start Experimental Smartwatch Bus
        try:
            from hecos.core.audio import smartwatch_bus
            smartwatch_bus.start(state=get_state_manager())
        except Exception as e:
            self.logger.warning(f"[WebUI] Smartwatch Bus could not start: {e}")

        def _run():
            try:
                webui_cfg = self.config_manager.config.get("plugins", {}).get("WEB_UI", {})
                
                # Calculate internal LAN IP
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(('10.254.254.254', 1))
                    lan_ip = s.getsockname()[0]
                    s.close()
                except Exception:
                    lan_ip = "127.0.0.1"

                # Check and Automate SSL mapping via extracted module
                from .server_ssl import ensure_ssl_context
                ssl_context = ensure_ssl_context(webui_cfg, lan_ip, self.config_manager, self.logger)
                
                use_https = webui_cfg.get("https_enabled", False)
                scheme = "https" if use_https and ssl_context else "http"

                self.logger.info(
                    f"[WebUI] 🚀 Server live (debug={debug_on}) → "
                    f"{scheme}://{lan_ip}:{self.port}/chat  |  "
                    f"{scheme}://{lan_ip}:{self.port}/hecos/config/ui"
                )
                
                try:
                    import flask.cli as _flask_cli
                    _flask_cli.show_server_banner = lambda *a, **kw: None
                except Exception:
                    pass

                if ssl_context:
                    app.run(host="0.0.0.0", port=self.port, debug=debug_on, use_reloader=False, ssl_context=ssl_context)
                else:
                    app.run(host="0.0.0.0", port=self.port, debug=debug_on, use_reloader=False)

            except Exception as e:
                self.logger.error(f"[WebUI] Flask exception: {e}")

        self._thread = threading.Thread(target=_run, daemon=True, name="HecosWebUIThread")
        self._thread.start()


def start_if_needed(config_manager, root_dir: str, port: int = 7070) -> None:
    """Singleton entry point — safe to call multiple times, even with two module instances."""
    # We use sys to share the singleton because this module is often double-imported
    # (once as __main__ and once as modules.web_ui.server).
    import sys
    
    # We also need a shared lock
    if not hasattr(sys, "_hecos_webui_lock"):
        import threading
        sys._hecos_webui_lock = threading.Lock()
    
    with sys._hecos_webui_lock:
        b_log = logging.getLogger("HecosWebUI")
        try:
            srv = getattr(sys, "_hecos_webui_instance", None)
            
            alive = (srv is not None
                     and srv._thread is not None
                     and srv._thread.is_alive())
            
            if not alive:
                b_log.info(f"[WebUI] Starting server on port {port}...")
                srv = HecosWebUIServer(config_manager, root_dir, port, logger=b_log)
                srv.start()
                setattr(sys, "_hecos_webui_instance", srv)
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

    # Force UTF-8 output encoding on Windows (prevents UnicodeEncodeError with emojis/box-drawing)
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except AttributeError:
            pass
    
    # We are in hecos/plugins/web_ui/server.py -> need 3 levels up to reach root
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(root)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    from hecos.app.config import ConfigManager
    from hecos.core.i18n.translator import init_translator
    from hecos.core.logging import logger
    from hecos.core.constants import LOGS_DIR
    cfg = ConfigManager()
    
    # Initialize basic logging (disable external windows for webui standalone)
    logger.init_logger(cfg.config, allow_external_windows=False)
    
    # Initialize translator with current config language
    init_translator(cfg.config.get("language", "en"))

    # Initialize memory vault (creates DB if not present)
    from hecos.memory.brain_interface import initialize_vault, maybe_clear_on_restart
    initialize_vault()
    maybe_clear_on_restart(cfg.config)
    
    # Initialize plugin registry (needed for plugin execution from WebUI process)
    from hecos.core.system import module_loader
    module_loader.update_capability_registry(cfg.config)
    
    # Initialize MCP Bridge for Universal External Tools
    mcp_bridge = module_loader.get_plugin_module("MCP_BRIDGE", legacy=False)
    if mcp_bridge and hasattr(mcp_bridge, "on_load"):
        try:
            logger.info("[WebUI Standalone] Bootstrapping MCP Bridge...")
            mcp_bridge.on_load(cfg.config)
        except Exception as mcp_e:
            logger.error(f"[WebUI Standalone] MCP Bridge bootstrap error: {mcp_e}")

    # Initialize state manager with config_audio.json settings
    from hecos.core.audio.device_manager import get_audio_config
    acfg = get_audio_config()
    
    sm = StateManager(
        initial_voice_status=acfg.get('voice_status', True),
        initial_listening_status=acfg.get('listening_status', True)
    )
    sm.push_to_talk    = acfg.get('push_to_talk', False)
    sm.ptt_hotkey      = acfg.get('ptt_hotkey', 'ctrl+shift')
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
        import json, os, time, tempfile
        hb_file = os.path.join(tempfile.gettempdir(), "hecos_webui_heartbeat.json")
        if not os.path.exists(hb_file): 
            return False
        try:
            with open(hb_file, "r") as f:
                data = json.load(f)
                # If any page (chat or config) checked in last 30 seconds, assume open
                now = time.time()
                for ts in data.values():
                    if now - ts < 30: return True
        except: pass
        return False

    # Auto-open browser in standalone mode ONLY if not already open
    # [Removed] - Auto-open logic is now fully managed by tray_app.py or plugin wrappers 
    # to avoid race conditions and redundant browser tabs.

    from hecos.core.system import instance_lock
    if not os.environ.get("HECOS_MONITORED_PROCESS"):
        if not instance_lock.acquire_lock("hecos_web"):
            print("\n[ERROR] Another instance of Hecos Web is already running.")
            sys.exit(1)

    start_if_needed(cfg, root, port=7070)



    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Hecos WebUI server stopped.")

