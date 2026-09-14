"""
hecos/modules/web_ui/routes_config_ui.py
Frontend rendering and UI shell routes for the configuration hub.
"""
import os
import time
from flask import render_template, jsonify
from hecos.core.logging import logger
from hecos.modules.web_ui.routes_config_api import _build_options_dict


# ── PANEL MAP: tab_id → template fragment ──────────────────────────────────
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
    'webui':           'modules/config_utils.html',
    'executor':        'modules/config_utils.html',
    'automation':      'modules/config_utils.html',
    'sysnet':          'modules/config_sysnet.html',
    'users':           'modules/config_users.html',
    'payload':         'modules/config_payload.html',
    'plugins':         'modules/config_plugins.html',
    'contacts':        'modules/config_contacts.html',
    'logs':            'modules/config_logs.html',
    'privacy':         'modules/config_privacy.html',
    'hpm-settings':    'modules/config_hpm_settings.html',
    'widgets':         'modules/config_widgets.html',
    'help':            'modules/config_help.html',
    'flows':           'modules/config_flows.html',
    'packages':        'modules/config_packages.html',
    'shortcuts':       'modules/config_shortcuts.html',
}

_PANELS_NEEDING_OPTIONS = {'backend', 'voice', 'ia', 'igen', 'media'}

_HPM_PANEL_CACHE: dict = {}

def clear_hpm_panel_cache():
    """Clears the HPM panel cache (called after a package install/uninstall)."""
    _HPM_PANEL_CACHE.clear()

def _discover_hpm_panel(panel_id: str) -> str | None:
    """Auto-discovers a config panel HTML template for HPM-installed packages."""
    if panel_id in _HPM_PANEL_CACHE:
        return _HPM_PANEL_CACHE[panel_id]

    base_dir   = os.path.dirname(__file__)
    tpl_dir    = os.path.join(base_dir, "templates")
    candidate  = os.path.join(tpl_dir, "modules", f"config_{panel_id}.html")
    if os.path.isfile(candidate):
        result = f"modules/config_{panel_id}.html"
        _HPM_PANEL_CACHE[panel_id] = result
        return result

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
                        basename = os.path.basename(tf)
                        candidate_verbatim = os.path.join(tpl_dir, "modules", basename)
                        if os.path.isfile(candidate_verbatim):
                            result = f"modules/{basename}"
                            _HPM_PANEL_CACHE[panel_id] = result
                            return result

                        install_path = pkg.get("install_path")
                        if install_path:
                            plugin_dir = manifest.get("plugin_dir") or pkg["id"]
                            tf_stripped = tf
                            prefix = plugin_dir.rstrip("/\\") + "/"
                            if tf_stripped.startswith(prefix):
                                tf_stripped = tf_stripped[len(prefix):]
                            abs_template = os.path.join(install_path, tf_stripped)
                            if os.path.isfile(abs_template):
                                result = f"HPM_RAW:{abs_template}"
                                _HPM_PANEL_CACHE[panel_id] = result
                                return result
    except Exception:
        pass

    _HPM_PANEL_CACHE[panel_id] = None
    return None


def register_config_ui_routes(app, cfg_mgr, get_sm=None):
    """Register frontend rendering endpoints for configuration."""
    
    _ui_cache: dict = {}

    @app.route("/hecos/config/ui")
    def config_ui():
        """Shell route — serves the lightweight Central Hub skeleton."""
        try:
            from hecos.core.i18n.translator import get_translator
            from flask_login import current_user as cu

            lang     = cfg_mgr.config.get("language", "en")
            user_id  = getattr(cu, "id", "anon") if cu.is_authenticated else "anon"
            cache_key = f"{lang}:{user_id}"
            now_ts   = time.monotonic()

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
            if len(_ui_cache) > 10:
                oldest_key = min(_ui_cache, key=lambda k: _ui_cache[k][0])
                _ui_cache.pop(oldest_key, None)
            return rendered
        except Exception as e:
            return f"<h1>Errore: index.html non trovato</h1><p>{str(e)}</p>", 500


    @app.route("/hecos/config/fragment/<panel_id>")
    def config_fragment(panel_id):
        """Lazy-load endpoint: returns a single config panel as an HTML fragment."""
        template_name = _PANEL_MAP.get(panel_id)

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
            zconfig_data = cfg_mgr.config
            
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
            import traceback as _tb
            logger.error(f"[WebUI] Fragment '{panel_id}' error: {e}\n{_tb.format_exc()}")
            return f"<p style='color:red'>Error loading panel <strong>{panel_id}</strong>: {e}</p>", 500


    @app.route("/api/hub/panels", methods=["GET"])
    def hub_panels():
        """Dynamic Central Hub: returns HPM-installed config panels."""
        try:
            from hecos.core.package_manager.registry import PackageRegistry
            import json as _json

            hecos_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            data_dir = os.path.join(hecos_root, "data")
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
                    continue

                plugin_id = pkg["id"]
                tab_id = cp.get("tab_id") or plugin_id.replace("_", "-")
                plugin_dir_prefix = (manifest.get("plugin_dir") or plugin_id).rstrip("/\\") + "/"
                js_file_raw  = cp.get("js_file")
                css_file_raw = cp.get("css_file")

                def _strip_prefix(raw):
                    if raw and raw.startswith(plugin_dir_prefix):
                        return raw[len(plugin_dir_prefix):]
                    return raw

                js_url  = f"hpm_plugin/{plugin_id}/{_strip_prefix(js_file_raw)}"  if js_file_raw  else None
                css_url = f"hpm_plugin/{plugin_id}/{_strip_prefix(css_file_raw)}" if css_file_raw else None

                panels.append({
                    "id":          tab_id,
                    "name":        pkg.get("name") or manifest.get("name", pkg["id"]),
                    "icon":        cp.get("tab_icon", ""),
                    "category":    cp.get("category", "CONNETTIV\u00c0"),
                    "plugin_tag":  manifest.get("tag", pkg["id"].upper()),
                    "version":     pkg.get("version", ""),
                    "type":        pkg.get("type") or manifest.get("type", "plugin"),
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
        if not re.match(r'^[a-z0-9_\-]+$', plugin_id):
            abort(404)
        hecos_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        plugin_base = os.path.join(hecos_root, "hpm", plugin_id)
        if not os.path.isdir(plugin_base):
            plugin_base = os.path.join(hecos_root, "hpm", "libraries", plugin_id)
        if not os.path.isdir(plugin_base):
            plugin_base = os.path.join(hecos_root, "hpm", "plugins", plugin_id)
        if not os.path.isdir(plugin_base):
            plugin_base = os.path.join(hecos_root, "modules", plugin_id)
        if not os.path.isdir(plugin_base):
            plugin_base = os.path.join(hecos_root, "plugins", plugin_id)

        try:
            safe_path = os.path.abspath(os.path.join(plugin_base, filename))
            if not safe_path.startswith(os.path.abspath(plugin_base)):
                abort(403)
            return send_from_directory(os.path.dirname(safe_path), os.path.basename(safe_path))
        except Exception as e:
            logger.warning(f"[WebUI] hpm_plugin_static error for {plugin_id}/{filename}: {e}")
            abort(404)
