"""
routes_config_core.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Core Configuration Routes
Handles UI shell, lazy panel fragment loading, and main system config CRUD.

Phase 2 enhancement: config_fragment auto-discovers templates for HPM packages
using the naming convention `modules/config_<panel_id>.html`, eliminating the
need to manually edit _PANEL_MAP for every new HPM package.
─────────────────────────────────────────────────────────────────────────────
"""
import os
import glob
import time
from flask import request, jsonify, render_template

# ── Server-side options cache ─────────────────────────────────────────────────
# Avoids expensive YAML reload + filesystem glob + personality sync on every
# tab click or /hecos/options request. Invalidated on config save or after TTL.
_OPTIONS_CACHE: dict = {}
_OPTIONS_CACHE_TS: float = 0.0
_OPTIONS_CACHE_TTL: float = 60.0  # seconds


def _invalidate_options_cache():
    """Call this after a config save to force a fresh build on next request."""
    global _OPTIONS_CACHE_TS
    _OPTIONS_CACHE_TS = 0.0


def _build_options_dict(cfg_mgr, fast=False):
    """Build the zoptions dict containing model lists, Piper voices, personalities.
    Results are cached in memory for _OPTIONS_CACHE_TTL seconds to avoid
    repeated disk I/O and filesystem scans on every tab click.
    Pass fast=False to force a full rebuild (used by /hecos/options endpoint).
    """
    global _OPTIONS_CACHE, _OPTIONS_CACHE_TS

    now = time.monotonic()
    # Return cached result if still valid
    if _OPTIONS_CACHE and (now - _OPTIONS_CACHE_TS) < _OPTIONS_CACHE_TTL:
        return _OPTIONS_CACHE

    # ── Full build ────────────────────────────────────────────────────────────
    cfg = cfg_mgr.config  # Use in-memory config; no disk reload needed here

    # Dynamically resolve Hecos root directory
    hecos_root  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    piper_path_dir = os.path.join(hecos_root, 'bin', 'piper')
    try:
        onnx_files = [os.path.basename(f) for f in glob.glob(os.path.join(piper_path_dir, "*.onnx"))]
        if not onnx_files:
            onnx_files = ["it_IT-aurora-medium.onnx"]
    except Exception:
        onnx_files = ["it_IT-aurora-medium.onnx"]

    from hecos.app.model_manager import ModelManager
    mm         = ModelManager(cfg_mgr)
    # Always use fast_mode=True for WebUI fragment requests — the slow network
    # fetch happens only via the background /hecos/options call from JS.
    categorized = mm.get_available_models(fast_mode=True)
    ollama_models = categorized.get("Ollama (Local)", [])

    # Sync personalities only if the cache is cold (avoid disk write per request)
    cfg_mgr.sync_available_personalities()
    personalita = list(cfg_mgr.config.get("ai", {}).get("available_personalities", {}).values())

    cloud_models_flat = []
    cloud_by_provider = {}
    for cat, models in categorized.items():
        if "Cloud" in cat:
            cloud_models_flat.extend(models)
            provider = cat.replace("Cloud (", "").replace(")", "").lower()
            cloud_by_provider[provider] = models

    result = {
        "piper_voices":  onnx_files,
        "piper_dir":     piper_path_dir,
        "ollama_models": ollama_models,
        "personalities": personalita,
        "cloud_models":  cloud_by_provider,
        "all_cloud":     cloud_models_flat,
    }

    # Store in cache
    _OPTIONS_CACHE    = result
    _OPTIONS_CACHE_TS = now
    return result


# ── PANEL MAP: tab_id → template fragment ──────────────────────────────────
# Keys MUST match the `id` fields in config_manifest.js CONFIG_HUB.modules
_PANEL_MAP = {
    'backend':         'modules/config_backend.html',
    'keymanager':      'modules/key_manager.html',
    'routing':         'modules/config_routing.html',
    'agent':           'modules/config_agent.html',
    'ia':              'modules/config_persona.html',
    'filters':         'modules/config_filters.html',
    'memory':          'modules/config_memory.html',
    'voice':           'modules/config_voice.html',
    'system':          'modules/config_system.html',
    'media':           'modules/config_media.html',
    'aesthetics':      'modules/config_styles.html',
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
    'contacts':        'modules/config_contacts.html',
    'mail':            'modules/config_mail.html',
    'templates':       'modules/config_templates.html',
    'weather_pro':     'modules/config_weather_pro.html',
    'mcp':             'modules/config_mcp.html',
    'messenger':       'modules/config_messenger.html',
    'remote-triggers': 'modules/config_remote_triggers.html',
    'drive':           'modules/config_drive.html',
    'drive-editor':    'modules/config_drive_editor.html',
    'logs':            'modules/config_logs.html',
    'privacy':         'modules/config_privacy.html',
    'hpm-settings':    'modules/config_hpm_settings.html',
    'widgets':         'modules/config_widgets.html',
    'help':            'modules/config_help.html',
    'flows':           'modules/config_flows.html',
    'lists':           'modules/config_lists.html',
    'backup':          'modules/config_backup.html',
    'packages':        'modules/config_packages.html',
}

# Panels that require zoptions (model lists, piper voices, personalities)
_PANELS_NEEDING_OPTIONS = {'backend', 'voice', 'ia', 'igen', 'media'}

# Cache: HPM panel template auto-discovery result (panel_id -> template_name)
_HPM_PANEL_CACHE: dict = {}


def clear_hpm_panel_cache():
    """Clears the HPM panel cache (called after a package install/uninstall)."""
    _HPM_PANEL_CACHE.clear()

def _discover_hpm_panel(panel_id: str) -> str | None:
    """
    Auto-discovers a config panel HTML template for HPM-installed packages.
    Results are cached in memory so repeated lookups are O(1).
    """
    if panel_id in _HPM_PANEL_CACHE:
        return _HPM_PANEL_CACHE[panel_id]

    base_dir   = os.path.dirname(__file__)
    tpl_dir    = os.path.join(base_dir, "templates")
    candidate  = os.path.join(tpl_dir, "modules", f"config_{panel_id}.html")
    if os.path.isfile(candidate):
        result = f"modules/config_{panel_id}.html"
        _HPM_PANEL_CACHE[panel_id] = result
        return result

    # Check directly via PackageRegistry for standalone plugins
    try:
        hecos_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(hecos_root, "data")
        from hecos.core.package_manager.registry import PackageRegistry
        reg = PackageRegistry(data_dir)
        import json as _json
        for pkg in reg.list_all():
            if pkg.get("status") == "disabled":
                continue
            manifest = pkg.get("manifest_snapshot") or {}
            if isinstance(manifest, str):
                try: manifest = _json.loads(manifest)
                except: manifest = {}
            cp = manifest.get("config_panel")
            if cp:
                tab_id = cp.get("tab_id") or pkg["id"].replace("_", "-")
                if tab_id == panel_id:
                    tf = cp.get("template_file")
                    if tf:
                        plugin_path = os.path.join(hecos_root, "plugins", pkg["id"])
                        abs_template = os.path.join(plugin_path, tf)
                        if os.path.isfile(abs_template):
                            result = f"HPM_RAW:{abs_template}"
                            _HPM_PANEL_CACHE[panel_id] = result
                            return result
    except Exception:
        pass

    _HPM_PANEL_CACHE[panel_id] = None
    return None


def init_config_core_routes(app, cfg_mgr, logger, get_sm=None):
    """Register core UI and system configuration routes."""

    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    # ── Rendered HTML shell cache ─────────────────────────────────────────────
    # The index.html render is the most expensive server-side operation:
    # Jinja injects 80KB i18n + 10KB config. Cache the output for a few seconds.
    _ui_cache: dict = {}

    @app.route("/hecos/config/ui")
    def config_ui():
        """Shell route — serves the lightweight Central Hub skeleton.
        Heavy options (model lists, Piper voices) are deferred until a specific
        panel is requested via /hecos/config/fragment/<panel_id>.
        Uses cfg_mgr.config (in-memory, no disk I/O) for fast TTFB.
        """
        try:
            from hecos.core.i18n.translator import get_translator
            from flask_login import current_user as cu
            import time as _t

            lang     = cfg_mgr.config.get("language", "en")
            user_id  = getattr(cu, "id", "anon") if cu.is_authenticated else "anon"
            cache_key = f"{lang}:{user_id}"
            now_ts   = _t.monotonic()

            # Return cached shell if still valid (10s TTL)
            cached = _ui_cache.get(cache_key)
            if cached and (now_ts - cached[0]) < 10.0:
                return cached[1]

            translations  = get_translator().get_translations()
            zconfig_data  = cfg_mgr.config
            rendered = render_template(
                "index.html",
                zconfig=zconfig_data,
                zoptions={},
                translations=translations,
            )
            _ui_cache[cache_key] = (now_ts, rendered)
            # Evict other keys to avoid memory growth on multi-user setups
            if len(_ui_cache) > 10:
                oldest_key = min(_ui_cache, key=lambda k: _ui_cache[k][0])
                _ui_cache.pop(oldest_key, None)
            return rendered
        except Exception as e:
            return f"<h1>Errore: index.html non trovato</h1><p>{str(e)}</p>", 500

    @app.route("/hecos/config/fragment/<panel_id>")
    def config_fragment(panel_id):
        """Lazy-load endpoint: returns a single config panel as an HTML fragment.
        Called by the frontend fetch engine when the user first clicks a tab.

        Resolution order:
          1. _PANEL_MAP (hardcoded core panels)
          2. HPM auto-discovery: modules/config_<panel_id>.html (no edit needed)
          3. 404 if neither found
        """
        template_name = _PANEL_MAP.get(panel_id)

        # Phase 2: HPM auto-discovery fallback (no _PANEL_MAP edit needed)
        if not template_name:
            template_name = _discover_hpm_panel(panel_id)

        if not template_name:
            return f"<p style='color:red'>Panel '{panel_id}' not found.</p>", 404

        try:
            from hecos.core.i18n.translator import get_translator
            from flask_login import current_user
            translations  = get_translator().get_translations()
            zoptions_data = {}
            if panel_id in _PANELS_NEEDING_OPTIONS:
                zoptions_data = _build_options_dict(cfg_mgr, fast=True)
            zconfig_data = cfg_mgr.config  # Use in-memory config
            
            # HPM raw templates (from plugin directory)
            if template_name.startswith("HPM_RAW:"):
                file_path = template_name.split("HPM_RAW:")[1]
                from flask import render_template_string
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return render_template_string(
                    content,
                    zconfig=zconfig_data,
                    zoptions=zoptions_data,
                    translations=translations,
                    current_user=current_user,
                )

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

    @app.route("/api/hub/panels", methods=["GET"])
    def hub_panels():
        """Dynamic Central Hub: returns HPM-installed config panels.
        The frontend mergeHubPanels() calls this endpoint to register tabs
        without requiring manual edits to config_manifest.js.
        
        Returns a list of panel descriptors:
          { id, name, icon, category, plugin_tag, version, description }
        """
        try:
            from hecos.core.package_manager.registry import PackageRegistry
            import json as _json

            hecos_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
            data_dir = os.path.join(hecos_root, "hecos", "data")
            reg      = PackageRegistry(data_dir)
            packages = reg.list_all()

            panels = []
            for pkg in packages:
                if pkg.get("status") == "disabled":
                    continue

                manifest = pkg.get("manifest_snapshot") or {}
                if isinstance(manifest, str):
                    try: manifest = _json.loads(manifest)
                    except: manifest = {}

                cp = manifest.get("config_panel")
                if not cp:
                    # No config panel declared → skip (don't add a tab)
                    continue

                # Build HPM-specific static paths using the dedicated /hpm/static/ route
                plugin_id = pkg["id"]
                tab_id = cp.get("tab_id") or plugin_id.replace("_", "-")
                js_file_raw = cp.get("js_file")
                css_file_raw = cp.get("css_file")
                
                js_url  = f"hpm_plugin/{plugin_id}/{js_file_raw}"  if js_file_raw  else None
                css_url = f"hpm_plugin/{plugin_id}/{css_file_raw}" if css_file_raw else None

                panels.append({
                    "id":          tab_id,
                    "name":        pkg.get("name") or manifest.get("name", pkg["id"]),
                    "icon":        cp.get("tab_icon", ""),
                    "category":    cp.get("category", "CONNETTIV\u00c0"),
                    "plugin_tag":  manifest.get("tag", pkg["id"].upper()),
                    "version":     pkg.get("version", ""),
                    "description": pkg.get("description", ""),
                    "js_file":     js_url,
                    "css_file":    css_url,
                })

            return jsonify(panels)
        except Exception as e:
            logger.warning(f"[WebUI] /api/hub/panels error: {e}")
            return jsonify([])

    @app.route("/hpm_plugin/<plugin_id>/<path:filename>")
    def hpm_plugin_static(plugin_id, filename):
        """Serve static assets (JS, CSS, images) from installed HPM plugins."""
        import re
        from flask import send_from_directory, abort
        # Security: only allow alphanumeric/underscore plugin IDs
        if not re.match(r'^[a-z0-9_\-]+$', plugin_id):
            abort(404)
        hecos_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        plugin_base = os.path.join(hecos_root, "hecos", "plugins", plugin_id)
        # Build the full path and ensure it stays within the plugin dir
        full_path = os.path.realpath(os.path.join(plugin_base, filename))
        plugin_base_real = os.path.realpath(plugin_base)
        if not full_path.startswith(plugin_base_real):
            abort(403)  # Path traversal attempt
        directory = os.path.dirname(full_path)
        basename = os.path.basename(full_path)
        try:
            return send_from_directory(directory, basename)
        except Exception:
            abort(404)

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

                # Invalidate the options cache so the next tab click gets fresh data
                _invalidate_options_cache()

                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/options", methods=["GET"])
    def get_options():
        return jsonify(_build_options_dict(cfg_mgr, fast=True))
