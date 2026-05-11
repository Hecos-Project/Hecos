import os
import json
from flask import request, jsonify, render_template

def init_config_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    def _build_options_dict(cfg_mgr, fast=False):
        import glob
        cfg = cfg_mgr.reload()
        
        # Dynamically resolve Hecos root directory
        hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        piper_path_dir = os.path.join(hecos_root, 'bin', 'piper')
        try:
            onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
            if not onnx_files: onnx_files = ["it_IT-aurora-medium.onnx"]
        except:
            onnx_files = ["it_IT-aurora-medium.onnx"]
            
        from app.model_manager import ModelManager
        mm = ModelManager(cfg_mgr)
        categorized = mm.get_available_models(fast_mode=fast)
        
        ollama_models = categorized.get("Ollama (Local)", [])
        
        # Ensure config.json is in sync with filesystem personalities before returning
        cfg_mgr.sync_available_personalities()
        cfg = cfg_mgr.reload()
        personalita = list(cfg.get("ai", {}).get("available_personalities", {}).values())
        
        # Flatten cloud models for the simple dropdown
        cloud_models_flat = []
        cloud_by_provider = {}
        for cat, models in categorized.items():
            if "Cloud" in cat:
                cloud_models_flat.extend(models)
                provider = cat.replace("Cloud (", "").replace(")", "").lower()
                cloud_by_provider[provider] = models
 
        return {
            "piper_voices": onnx_files,
            "piper_dir":    piper_path_dir,
            "ollama_models": ollama_models,
            "personalities": personalita,
            "cloud_models":  cloud_by_provider,
            "all_cloud":     cloud_models_flat
        }

    @app.route("/hecos/config/ui")
    def config_ui():
        """Shell route — serves the lightweight Central Hub skeleton.
        Heavy options (model lists, Piper voices) are deferred until a specific
        panel is requested via /hecos/config/fragment/<panel_id>.
        """
        try:
            from hecos.core.i18n.translator import get_translator
            translations = get_translator().get_translations()
            # Lightweight: just reload config (no filesystem scans)
            # sync_available_personalities() is called lazily in the fragment route.
            zconfig_data = cfg_mgr.reload()
            return render_template(
                "index.html",
                zconfig=zconfig_data,
                zoptions={},
                translations=translations
            )
        except Exception as e:
            return f"<h1>Errore: index.html non trovato</h1><p>{str(e)}</p>", 500

    # ── PANEL MAP: tab_id → template fragment ──────────────────────────────────
    # Keys MUST match the `id` fields in config_manifest.js CONFIG_HUB.modules
    _PANEL_MAP = {
        'backend':        'modules/config_backend.html',
        'keymanager':     'modules/key_manager.html',
        'routing':        'modules/config_routing.html',
        'agent':          'modules/config_agent.html',
        'ia':             'modules/config_persona.html',
        'filters':        'modules/config_filters.html',
        'bridge':         'modules/config_bridge.html',
        'memory':         'modules/config_memory.html',
        'voice':          'modules/config_voice.html',
        'system':         'modules/config_system.html',
        'media':          'modules/config_media.html',
        'aesthetics':     'modules/config_styles.html',
        'igen':           'modules/config_igen.html',
        'webui':          'modules/config_utils.html',
        'browser':        'modules/config_browser.html',
        'sysnet':         'modules/config_sysnet.html',
        'users':          'modules/config_users.html',
        'security':       'modules/config_security.html',
        'payload':        'modules/config_payload.html',
        'plugins':        'modules/config_plugins.html',
        'reminder':       'modules/config_reminder.html',
        'calendar':       'modules/config_calendar.html',
        'studio':         'modules/config_plugin_studio.html',
        'mcp':            'modules/config_mcp.html',
        'remote-triggers':'modules/config_remote_triggers.html',
        'drive':          'modules/config_drive.html',
        'drive-editor':   'modules/config_drive_editor.html',
        'logs':           'modules/config_logs.html',
        'privacy':        'modules/config_privacy.html',
        'help':           'modules/config_help.html',
    }

    # Panels that require zoptions (model lists, piper voices, personalities)
    _PANELS_NEEDING_OPTIONS = {'backend', 'voice', 'ia', 'igen', 'media'}

    @app.route("/hecos/config/fragment/<panel_id>")
    def config_fragment(panel_id):
        """Lazy-load endpoint: returns a single config panel as an HTML fragment.
        Called by the frontend fetch engine when the user first clicks a tab.
        Options are built only for panels that actually need them.
        """
        template_name = _PANEL_MAP.get(panel_id)
        if not template_name:
            return f"<p style='color:red'>Panel '{panel_id}' not found.</p>", 404

        try:
            from hecos.core.i18n.translator import get_translator
            translations = get_translator().get_translations()
            zoptions_data = {}

            if panel_id in _PANELS_NEEDING_OPTIONS:
                # Run the heavy scan only for the panels that need model/personality lists
                zoptions_data = _build_options_dict(cfg_mgr, fast=True)
            
            zconfig_data = cfg_mgr.reload()
            from flask_login import current_user
            return render_template(
                template_name,
                zconfig=zconfig_data,
                zoptions=zoptions_data,
                translations=translations,
                current_user=current_user
            )
        except Exception as e:
            logger.error(f"[WebUI] Fragment '{panel_id}' error: {e}")
            return f"<p style='color:red'>Error loading panel: {e}</p>", 500

    @app.route("/hecos/config", methods=["GET"])
    def get_config():
        cfg = cfg_mgr.reload()
        return jsonify(cfg)

    @app.route("/hecos/config", methods=["POST"])
    def post_config():
        try:
            incoming = request.get_json(force=True)
            
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400
            # Estrai il flag custom Frontend per forzare il riavvio (o auto-save silenzioso)
            force_restart = incoming.pop("_force_restart", False)
            
            # DEBUG: Log the full AI block we receive
            ai_block = incoming.get("ai", {})
            logger.info(f"[CONFIG-DEBUG] Incoming payload - ai.active_personality: {ai_block.get('active_personality', '<<NOT PRESENT>>')}")
            
            save_result = cfg_mgr.update_config(incoming)
            logger.info(f"[CONFIG-DEBUG] update_config returned: {save_result}")
            
            if save_result:
                # Dynamically update the global translator language without reboot
                from hecos.core.i18n.translator import get_translator
                get_translator().set_language(incoming.get("language", "en"))
                
                # Keep state_manager in sync with toggles
                sm = _sm()
                if sm is not None:
                    # Update local state based on config toggles
                    sm.listening_status = incoming.get("listening", {}).get("enabled", sm.listening_status)
                # Update the processor and registry at runtime
                try:
                    from hecos.core.processing import processore, filtri
                    from hecos.core.system import module_loader
                    processore.configure(cfg_mgr.config)
                    module_loader.update_capability_registry(cfg_mgr.config, debug_log=False)
                    filtri.reset_cache()
                except Exception as e:
                    logger.debug(f"[WebUI] Processor runtime sync error: {e}")
                    
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500


    @app.route("/hecos/options", methods=["GET"])
    def get_options():
        return jsonify(_build_options_dict(cfg_mgr))

    @app.route("/hecos/api/config/media", methods=["GET"])
    def get_media_config_api():
        from hecos.core.media_config import get_media_config
        return jsonify(get_media_config())

    @app.route("/hecos/api/config/media", methods=["POST"])
    def post_media_config_api():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                 return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            from hecos.core.media_config import save_media_config, get_media_config
            cfg = get_media_config()
            
            # Deep update
            igen = incoming.get("image_gen", {})
            save_to_env = igen.pop("_internal_save_to_env", False)
            logger.info(f"[WebUI] Media Save. save_to_env={save_to_env}")
            
            for key, val in incoming.items():
                if isinstance(val, dict) and key in cfg and isinstance(cfg[key], dict):
                    cfg[key].update(val)
                else:
                    cfg[key] = val
            
            # If requested, save the key to the environment file (pool)
            if save_to_env:
                try:
                    api_key = igen.get("api_key", "").strip()
                    provider = igen.get("provider", "huggingface").strip().lower()
                    comment = igen.get("api_key_comment", "").strip()
                    logger.info(f"[WebUI] Attempting key persistence. Provider={provider}, KeyLen={len(api_key)}")
                    if api_key:
                        from hecos.core.keys.key_manager import get_key_manager
                        res = get_key_manager().add_key(provider, api_key, comment, save_to_env=True)
                        logger.info(f"[WebUI] Key persistence result: {res}")
                    else:
                        logger.warning("[WebUI] Save to .env requested but api_key is empty.")
                except Exception as e:
                    logger.error(f"[WebUI] Error saving key to .env: {e}")

            if save_media_config(cfg):
                logger.info("[WebUI] Media configuration saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/api/config/media error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/config/routing", methods=["GET"])
    def get_routing_config():
        try:
            from hecos.config import load_yaml
            from hecos.config.schemas.routing_schema import RoutingOverrides
            path = os.path.join(root_dir, "hecos", "config", "data", "routing_overrides.yaml")
            model = load_yaml(path, RoutingOverrides)
            return jsonify(model.overrides)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/hecos/config/routing", methods=["POST"])
    def post_routing_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            from hecos.config import save_yaml
            from hecos.config.schemas.routing_schema import RoutingOverrides
            path = os.path.join(root_dir, "hecos", "config", "data", "routing_overrides.yaml")
            
            # Re-validate and save
            model = RoutingOverrides(overrides=incoming)
            if save_yaml(path, model):
                logger.info("[WebUI] Routing overrides saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/config/routing error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/config/agent", methods=["GET"])
    def get_agent_config():
        try:
            from hecos.config import load_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            path = os.path.join(root_dir, "hecos", "config", "data", "agent.yaml")
            model = load_yaml(path, AgentConfig)
            return jsonify(model.model_dump())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/hecos/config/agent", methods=["POST"])
    def post_agent_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400
            
            from hecos.config import save_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            path = os.path.join(root_dir, "hecos", "config", "data", "agent.yaml")
            
            # Re-validate and save
            model = AgentConfig(**incoming)
            if save_yaml(path, model):
                logger.info("[WebUI] Agent configuration saved successfully.")
                # We update the loop config dynamically if it was cached (AgentExecutor loads on init but let's be safe)
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/config/agent error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/plugins/registry", methods=["GET"])
    def get_plugin_registry():
        try:
            from hecos.core.system.module_state import REGISTRY_PATH
            if os.path.exists(REGISTRY_PATH):
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    return jsonify(json.load(f))
            return jsonify({})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/webui/state', methods=['GET', 'POST'])
    def handle_ui_state():
        state_file = os.path.join(root_dir, 'hecos', 'core', 'config', 'ui_state.json')
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        
        if request.method == 'POST':
            try:
                state = request.get_json()
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=4)
                return jsonify({"status": "success"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
                
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return jsonify(json.load(f))
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        return jsonify({})
