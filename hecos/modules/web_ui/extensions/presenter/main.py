import os
from flask import send_from_directory, request, jsonify
from hecos.core.logging import logger
from .config.store import load_presenter_config

def init_routes(app, root_dir: str = None):
    logger.info("[Presenter] Initializing routes...")
    cfg = load_presenter_config()
    
    
    if not getattr(cfg, 'enabled', True):
        logger.info("[Presenter] Module is disabled in configuration.")
    else:
        from .engine import get_engine
        get_engine().start()
    
    _static_dir = os.path.join(os.path.dirname(__file__), "static")
    @app.route("/ext/presenter/static/<path:filename>")
    def presenter_static(filename):
        return send_from_directory(_static_dir, filename)

    @app.route("/api/ext/presenter/config", methods=["GET"])
    def get_presenter_config():
        from .config.store import load_presenter_config
        cfg = load_presenter_config()
        return jsonify({"ok": True, "config": cfg.model_dump()})

    @app.route("/api/ext/presenter/config", methods=["POST"])
    def post_presenter_config():
        try:
            from .config.store import load_presenter_config, save_presenter_config
            
            data = request.json or {}
            cfg = load_presenter_config()
            
            if 'enabled' in data: cfg.enabled = data['enabled']
            if 'allow_commands' in data: cfg.allow_commands = data['allow_commands']
            if 'panel_default' in data: cfg.panel_default = data['panel_default']
            if 'live_commentary' in data: cfg.live_commentary = data['live_commentary']
            if 'commentary_on_messages' in data: cfg.commentary_on_messages = data['commentary_on_messages']
            if 'verbosity' in data: cfg.verbosity = data['verbosity']
            if 'briefing_on_new_chat' in data: cfg.briefing_on_new_chat = data['briefing_on_new_chat']
            
            if 'voice' in data:
                v = data['voice']
                if 'preset_id' in v: cfg.voice.preset_id = v['preset_id']
                if 'max_tokens' in v: cfg.voice.max_tokens = v['max_tokens']
                
            save_presenter_config(cfg)
            
            from .engine import get_engine
            if cfg.enabled:
                get_engine().start()
            
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[Presenter] Error saving config: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/ext/presenter/test", methods=["POST"])
    def test_presenter():
        """Manual trigger for testing."""
        try:
            from .engine import get_engine
            from .feed import add_feed_entry
            from hecos.core.events import emit
            
            engine = get_engine()
            cfg = engine.cfg
            
            logger.info(f"[Presenter] TEST: enabled={cfg.enabled}, live_commentary={cfg.live_commentary}, preset_id={cfg.voice.preset_id}")
            logger.info(f"[Presenter] TEST: engine._running={engine._running}")
            
            add_feed_entry("test", "This is a direct test message from the Presenter.", persist=cfg.feed.persist)
            emit("persona_switched", {"new_persona": "Test Persona"})
            logger.info("[Presenter] TEST: persona_switched event emitted.")
            
            return jsonify({"ok": True, "message": "Test triggered. Check chat for output.", "config": {
                "enabled": cfg.enabled,
                "live_commentary": cfg.live_commentary,
                "preset_id": cfg.voice.preset_id,
                "running": engine._running,
            }})
        except Exception as e:
            logger.error(f"[Presenter] TEST error: {e}")
            import traceback
            return jsonify({"ok": False, "error": str(e), "traceback": traceback.format_exc()}), 500

    @app.route("/api/ext/presenter/briefing", methods=["GET"])
    def get_briefing():
        """System briefing: checks port, backend, Ollama, CDP, active persona."""
        items = []
        
        # Use the same config loading as the engine
        try:
            from hecos.core.llm.brain import load_config
            config = load_config() or {}
        except Exception as e:
            logger.warning(f"[Presenter] Briefing: could not load config via brain: {e}")
            try:
                import sys
                cfg_mgr = getattr(sys, 'hecos_config_manager', None)
                config = cfg_mgr.config if cfg_mgr else {}
            except Exception:
                config = {}

        # 1. Server port
        try:
            port = config.get("plugins", {}).get("WEB_UI", {}).get("port", 7070)
            items.append({"type": "system_info", "text": f"Hecos active on port {port}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing port error: {e}")

        # 2. Backend type & model
        try:
            backend_type = config.get("backend", {}).get("type", "ollama")
            model = config.get("backend", {}).get(backend_type, {}).get("model", "unknown")
            items.append({"type": "system_status", "text": f"Backend: {backend_type} · Model: {model}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing backend error: {e}")

        # 3. Ollama check
        try:
            backend_type = config.get("backend", {}).get("type", "ollama")
            if backend_type == "ollama":
                try:
                    import requests as _req
                    r = _req.get("http://localhost:11434/api/tags", timeout=2)
                    if r.status_code == 200:
                        models = r.json().get("models", [])
                        items.append({"type": "system_status", "text": f"Ollama online — {len(models)} models available"})
                    else:
                        items.append({"type": "system_warning", "text": "Ollama responded with an error"})
                except Exception:
                    items.append({"type": "system_warning", "text": "Ollama unreachable on localhost:11434"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing Ollama error: {e}")

        # 4. CDP Mode
        try:
            import socket
            def _is_port_open(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('127.0.0.1', port)) == 0

            cdp_port = int(config.get("plugins", {}).get("CDP", {}).get("port", 9222))
            
            if _is_port_open(cdp_port):
                items.append({"type": "system_status", "text": f"TCP Protocol: Active — Port {cdp_port} connected (CDP Mode)"})
            else:
                items.append({"type": "system_warning", "text": f"TCP/CDP Mode inactive. Browser automations disabled."})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing CDP error: {e}")

        # 5. Active persona
        try:
            persona = config.get("ai", {}).get("active_personality", "")
            if persona and persona not in ("", "default"):
                persona_name = persona.replace(".yaml", "").replace("_", " ").title()
                items.append({"type": "system_info", "text": f"Active persona: {persona_name}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing persona error: {e}")

        # 6. Presenter preset
        try:
            p_cfg = load_presenter_config()
            if p_cfg.voice.preset_id:
                from hecos.core.global_presets.manager import get_soul
                soul = get_soul(p_cfg.voice.preset_id)
                if soul:
                    items.append({"type": "system_info", "text": f"Presenter Global Preset: {soul.meta.name}"})
        except Exception as e:
            logger.debug(f"[Presenter] Briefing preset error: {e}")

        # 7. Tips
        hdcs_key_display = "Ctrl + Space"
        try:
            from hecos.modules.web_ui.routes_shortcuts import _load_user_shortcuts
            from flask_login import current_user
            username = current_user.username if hasattr(current_user, 'username') else "admin"
            actual_root = root_dir if root_dir else os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            user_shortcuts = _load_user_shortcuts(actual_root, username)
            hdcs_key = user_shortcuts["bindings"].get("ui.open_hdcs", "ctrl+space")
            hdcs_key_display = hdcs_key.replace("+", " + ").title()
        except Exception as e:
            logger.debug(f"[Presenter] Could not load shortcut for tip: {e}")

        items.append({"type": "tip", "text": f"Type / in chat or press {hdcs_key_display} to open the Command Palette (HDCS)"})

        logger.info(f"[Presenter] Briefing generated {len(items)} items")
        return jsonify({"ok": True, "items": items})

    @app.route("/api/ext/presenter/feed", methods=["GET"])
    def get_feed():
        """Returns recent feed entries from the JSONL file."""
        try:
            import json
            from hecos.core.constants import LOGS_DIR
            feed_file = os.path.join(LOGS_DIR, "presenter_feed.jsonl")
            entries = []
            if os.path.exists(feed_file):
                with open(feed_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            # Return last N entries
            max_items = request.args.get("limit", 20, type=int)
            return jsonify({"ok": True, "entries": entries[-max_items:]})
        except Exception as e:
            logger.error(f"[Presenter] Feed read error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

