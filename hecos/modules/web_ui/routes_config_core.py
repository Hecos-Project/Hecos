"""
routes_config_core.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Core Configuration Routes
Handles UI shell, lazy panel fragment loading, and main system config CRUD.
─────────────────────────────────────────────────────────────────────────────
"""
import os
import glob
from flask import request, jsonify, render_template


def _build_options_dict(cfg_mgr, fast=False):
    """Build the zoptions dict containing model lists, Piper voices, personalities."""
    cfg = cfg_mgr.reload()

    # Dynamically resolve Hecos root directory
    hecos_root  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    piper_path_dir = os.path.join(hecos_root, 'bin', 'piper')
    try:
        onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
        if not onnx_files:
            onnx_files = ["it_IT-aurora-medium.onnx"]
    except Exception:
        onnx_files = ["it_IT-aurora-medium.onnx"]

    from app.model_manager import ModelManager
    mm         = ModelManager(cfg_mgr)
    categorized = mm.get_available_models(fast_mode=fast)
    ollama_models = categorized.get("Ollama (Local)", [])

    cfg_mgr.sync_available_personalities()
    cfg = cfg_mgr.reload()
    personalita = list(cfg.get("ai", {}).get("available_personalities", {}).values())

    cloud_models_flat = []
    cloud_by_provider = {}
    for cat, models in categorized.items():
        if "Cloud" in cat:
            cloud_models_flat.extend(models)
            provider = cat.replace("Cloud (", "").replace(")", "").lower()
            cloud_by_provider[provider] = models

    return {
        "piper_voices":  onnx_files,
        "piper_dir":     piper_path_dir,
        "ollama_models": ollama_models,
        "personalities": personalita,
        "cloud_models":  cloud_by_provider,
        "all_cloud":     cloud_models_flat,
    }


# ── PANEL MAP: tab_id → template fragment ──────────────────────────────────
# Keys MUST match the `id` fields in config_manifest.js CONFIG_HUB.modules
_PANEL_MAP = {
    'backend':         'modules/config_backend.html',
    'keymanager':      'modules/key_manager.html',
    'routing':         'modules/config_routing.html',
    'agent':           'modules/config_agent.html',
    'ia':              'modules/config_persona.html',
    'filters':         'modules/config_filters.html',
    'bridge':          'modules/config_bridge.html',
    'memory':          'modules/config_memory.html',
    'voice':           'modules/config_voice.html',
    'system':          'modules/config_system.html',
    'media':           'modules/config_media.html',
    'aesthetics':      'modules/config_styles.html',
    'igen':            'modules/config_igen.html',
    'webui':           'modules/config_utils.html',
    'web':             'modules/config_utils.html',
    'webcam':          'modules/config_utils.html',
    'executor':        'modules/config_utils.html',
    'automation':      'modules/config_utils.html',

    'browser':         'modules/config_browser.html',
    'sysnet':          'modules/config_sysnet.html',
    'users':           'modules/config_users.html',
    'security':        'modules/config_security.html',
    'payload':         'modules/config_payload.html',
    'plugins':         'modules/config_plugins.html',
    'reminder':        'modules/config_reminder.html',
    'calendar':        'modules/config_calendar.html',
    'mcp':             'modules/config_mcp.html',
    'remote-triggers': 'modules/config_remote_triggers.html',
    'drive':           'modules/config_drive.html',
    'drive-editor':    'modules/config_drive_editor.html',
    'logs':            'modules/config_logs.html',
    'privacy':         'modules/config_privacy.html',
    'widgets':         'modules/config_widgets.html',
    'help':            'modules/config_help.html',
}

# Panels that require zoptions (model lists, piper voices, personalities)
_PANELS_NEEDING_OPTIONS = {'backend', 'voice', 'ia', 'igen', 'media'}


def init_config_core_routes(app, cfg_mgr, logger, get_sm=None):
    """Register core UI and system configuration routes."""

    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/hecos/config/ui")
    def config_ui():
        """Shell route — serves the lightweight Central Hub skeleton.
        Heavy options (model lists, Piper voices) are deferred until a specific
        panel is requested via /hecos/config/fragment/<panel_id>.
        """
        try:
            from hecos.core.i18n.translator import get_translator
            translations  = get_translator().get_translations()
            zconfig_data  = cfg_mgr.reload()
            return render_template(
                "index.html",
                zconfig=zconfig_data,
                zoptions={},
                translations=translations,
            )
        except Exception as e:
            return f"<h1>Errore: index.html non trovato</h1><p>{str(e)}</p>", 500

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
            from flask_login import current_user
            translations  = get_translator().get_translations()
            zoptions_data = {}
            if panel_id in _PANELS_NEEDING_OPTIONS:
                zoptions_data = _build_options_dict(cfg_mgr, fast=True)
            zconfig_data = cfg_mgr.reload()
            return render_template(
                template_name,
                zconfig=zconfig_data,
                zoptions=zoptions_data,
                translations=translations,
                current_user=current_user,
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

            # Extract flag for optional force-restart (currently informational only)
            incoming.pop("_force_restart", False)

            # ── AGENT block: proxy to agent.yaml via dedicated save path ──────
            agent_block = incoming.pop("agent", None)
            if agent_block and isinstance(agent_block, dict):
                try:
                    from hecos.config import save_yaml
                    from hecos.config.schemas.agent_schema import AgentConfig
                    root_dir   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    agent_path = os.path.join(root_dir, "hecos", "config", "data", "agent.yaml")
                    save_yaml(agent_path, AgentConfig(**agent_block))
                    logger.debug("[CONFIG] agent.yaml updated from main payload.")
                except Exception as e:
                    logger.warning(f"[CONFIG] Could not save agent block: {e}")

            # DEBUG: Log the full AI block we receive
            ai_block  = incoming.get("ai", {})
            cal_block = incoming.get("extensions", {}).get("calendar", {})
            logger.info(f"[CONFIG-DEBUG] Incoming payload - ai.active_personality: {ai_block.get('active_personality', '<<NOT PRESENT>>')}")
            if cal_block:
                logger.info(f"[CONFIG-DEBUG] Incoming calendar payload: {cal_block.get('calendar_locale')} / {cal_block.get('calendar_country')}")
            else:
                logger.info("[CONFIG-DEBUG] Incoming payload HAS NO CALENDAR EXTENSION BLOCK.")

            save_result = cfg_mgr.update_config(incoming)
            logger.info(f"[CONFIG-DEBUG] update_config returned: {save_result}")

            if save_result:
                # ── Language runtime update: read from SAVED config ──
                # CRITICAL: do NOT use `incoming.get('language', 'en')` as default.
                # Partial saves (e.g. calendar auto-save with only `extensions:`)
                # don't include `language`, so 'en' fallback silently resets it.
                try:
                    from hecos.core.i18n.translator import get_translator
                    saved_lang = cfg_mgr.get("language") or "en"
                    get_translator().set_language(saved_lang)
                except Exception:
                    pass

                # Keep state_manager in sync with toggles
                sm = _sm()
                if sm is not None:
                    sm.listening_status = incoming.get("listening", {}).get("enabled", sm.listening_status)

                # Update processor and module registry at runtime (background thread to prevent locking UI)
                def _bg_sync(cfg_snapshot):
                    try:
                        from hecos.core.processing import processore, filtri
                        from hecos.core.system import module_loader
                        processore.configure(cfg_snapshot)
                        module_loader.update_capability_registry(cfg_snapshot, debug_log=False)
                        filtri.reset_cache()
                        logger.debug("[WebUI] Background processor sync completed.")
                    except Exception as e:
                        logger.debug(f"[WebUI] Processor background sync error: {e}")

                import threading
                import copy
                threading.Thread(target=_bg_sync, args=(copy.deepcopy(cfg_mgr.config),), daemon=True).start()

                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/options", methods=["GET"])
    def get_options():
        return jsonify(_build_options_dict(cfg_mgr))
