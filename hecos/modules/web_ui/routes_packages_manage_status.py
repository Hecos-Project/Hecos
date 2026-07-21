"""
routes_packages_manage.py
─────────────────────────────────────────────────────────────────────────────
Get, update status, and delete packages.
"""
from __future__ import annotations
import os
from flask import jsonify, request
from flask_login import login_required

from hecos.modules.web_ui.routes_packages_helpers import (
    _get_hpm_components,
    _refresh_jinja_loader,
    _hpm_event_broadcast
)
def _invalidate_all_caches():
    """Invalidate packages and widgets caches after any package state change."""
    try:
        from hecos.modules.web_ui.routes_packages_list import invalidate_packages_cache
        invalidate_packages_cache()
    except Exception:
        pass
    try:
        from hecos.modules.web_ui.routes_widgets_api import invalidate_widgets_cache
        invalidate_widgets_cache()
    except Exception:
        pass

def _hot_reload_registry(cfg_mgr, log=None):
    """Hot-reload the capability registry (tools, slash commands) using the live config manager."""
    try:
        from hecos.core.system import module_loader
        module_loader.update_capability_registry(cfg_mgr.config, debug_log=False)
        if log:
            log.info("[HPM] Capability registry hot-reloaded.")
    except Exception as e:
        if log:
            log.warning(f"[HPM] Capability registry reload failed (non-critical): {e}")
    try:
        from hecos.core.commands.registry import get_registry
        get_registry(reload=True)
    except Exception:
        pass

def register_manage_status_routes(app, _hecos_src: str, cfg_mgr, log):
    @app.route("/api/packages/<pkg_id>/status", methods=["PATCH"])
    @login_required
    def api_set_package_status(pkg_id):
        """
        Set a package status: 'installed' (enabled) or 'disabled'.
        Body: { "status": "disabled" }
        """
        data = request.get_json(silent=True) or {}
        status = data.get("status")
        if status not in ("installed", "disabled"):
            return jsonify({
                "ok": False,
                "error": "Status must be 'installed' or 'disabled'"
            }), 400
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            pkg = registry.get(pkg_id)
            if not pkg:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404

            # Extract snap and tag first so they are always available for the response
            import json as _json
            snap = pkg.get("manifest_snapshot", {})
            if isinstance(snap, str):
                try: snap = _json.loads(snap)
                except: snap = {}
            pkg_tag = snap.get("tag") or pkg_id.upper()
            panel_id = (snap.get("config_panel") or {}).get("tab_id") or pkg_id

            ok = registry.set_status(pkg_id, status)
            if ok:
                if status == "disabled":
                    # ── Call on_unload() on the plugin if it defines one ───────────
                    try:
                        from hecos.core.system import module_state
                        loaded_mod = module_state._loaded_plugins.get(pkg_tag)
                        if loaded_mod and hasattr(loaded_mod, "on_unload") and callable(loaded_mod.on_unload):
                            loaded_mod.on_unload()
                            log.info(f"[HPM] on_unload() called for '{pkg_tag}'.")
                    except Exception as _ul_e:
                        log.warning(f"[HPM] on_unload() error for '{pkg_tag}': {_ul_e}")
                    # ─────────────────────────────────────────────────────────────

                    widgets_modified = 0
                    for w in snap.get("widgets", []):
                        ext_id = w.get("id")
                        if ext_id:
                            cfg_mgr.set(False, "widgets", "per_widget", ext_id, "enabled")
                            cfg_mgr.set(False, "widgets", "per_widget", ext_id, "visible")
                            cfg_mgr.set(False, "widgets", "per_widget", ext_id, "room_visible")
                            widgets_modified += 1
                    if widgets_modified > 0:
                        cfg_mgr.save()
                elif status == "installed":
                    widgets_modified = 0
                    for w in snap.get("widgets", []):
                        ext_id = w.get("id")
                        if ext_id:
                            cfg_mgr.set(True, "widgets", "per_widget", ext_id, "enabled")
                            cfg_mgr.set(True, "widgets", "per_widget", ext_id, "visible")
                            cfg_mgr.set(True, "widgets", "per_widget", ext_id, "room_visible")
                            widgets_modified += 1
                    if widgets_modified > 0:
                        cfg_mgr.save()

                _hpm_event_broadcast("hpm:package_status_changed", {
                    "id": pkg_id, "status": status
                })
                _invalidate_all_caches()
                _hot_reload_registry(cfg_mgr, log)
            return jsonify({"ok": ok, "id": pkg_id, "status": status, "tag": pkg_tag, "panel_id": panel_id})
        except Exception as e:
            log.error(f"[HPM] PATCH /api/packages/{pkg_id}/status error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/hot_reload", methods=["POST"])
    @login_required
    def api_packages_hot_reload():
        """
        Manually trigger a hot-reload of the HPM capability registry.
        Rescans hpm/, modules/, plugins/ and updates the LLM tool registry,
        slash command registry and HPM panel cache — without a full restart.
        """
        try:
            _hot_reload_registry(cfg_mgr, log)
            try:
                from hecos.core.system.extension_loader import discover_webui_extensions, load_eager_extensions
                webui_ext_dir = os.path.join(_hecos_src, "modules", "web_ui")
                discover_webui_extensions(webui_ext_dir)
                load_eager_extensions(app, "WEB_UI")
            except Exception as _ext_e:
                log.warning(f"[HPM:HotReload] Extension re-discovery failed: {_ext_e}")

            _refresh_jinja_loader(app)

            try:
                from hecos.modules.web_ui.routes_config_core import clear_hpm_panel_cache
                clear_hpm_panel_cache()
            except ImportError:
                pass

            _invalidate_all_caches()
            _hpm_event_broadcast("hpm:registry_refreshed", {})
            log.info("[HPM] Manual hot-reload completed.")
            return jsonify({"ok": True, "message": "Capability registry reloaded."})
        except Exception as e:
            log.error(f"[HPM] Hot-reload error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/<pkg_id>/hot_reload_module", methods=["POST"])
    @login_required
    def api_hot_reload_single_module(pkg_id):
        """
        Hot-reload a single SDK module subprocess and refresh capabilities.
        """
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            pkg = registry.get(pkg_id)
            if not pkg:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404

            snap = pkg.get("manifest_snapshot", {})
            if isinstance(snap, str):
                import json
                try: snap = json.loads(snap)
                except: snap = {}

            tag = snap.get("tag") or pkg_id.upper()

            from hecos.core.module_bus import get_bus
            bus = get_bus()
            restarted = bus.restart_module(tag)

            if restarted:
                _hot_reload_registry(cfg_mgr, log)
                _invalidate_all_caches()
                log.info(f"[HPM] Single module hot-reload completed for '{tag}'.")
                return jsonify({"ok": True, "message": f"Module '{tag}' reloaded successfully (subprocess restart)."})
            else:
                # Fallback: reload in-process lazy/native plugin
                import sys, importlib.util
                from hecos.core.system import module_state

                reloaded = False
                reloaded_info = ""

                pkg = registry.get(pkg_id)
                install_path = pkg.get("install_path", "") if pkg else ""
                main_file = os.path.join(install_path, "plugin", "main.py") if install_path else None
                
                if main_file and os.path.exists(main_file):
                    try:
                        module_name = f"hecos.hpm.{pkg_id}.main"
                        parent_name = module_name.rsplit('.', 1)[0]
                        
                        # 1. Purge all submodules of this plugin from sys.modules
                        # This ensures multi-file plugins (like browser with engine.py, reader.py)
                        # are fully re-evaluated from disk.
                        modules_to_remove = [m for m in sys.modules.keys() if m.startswith(parent_name)]
                        for m in modules_to_remove:
                            del sys.modules[m]

                        # 2. Re-import from scratch
                        spec = importlib.util.spec_from_file_location(module_name, main_file)
                        if spec:
                            new_module = importlib.util.module_from_spec(spec)
                            if parent_name not in sys.modules:
                                sys.modules[parent_name] = type(sys)(parent_name)
                                sys.modules[parent_name].__path__ = [os.path.dirname(main_file)]
                            spec.loader.exec_module(new_module)
                            module_state._loaded_plugins[tag] = new_module
                            reloaded = True
                            reloaded_info = "full package re-imported"
                            log.info(f"[HPM] In-process plugin '{tag}' fully re-imported from disk.")
                    except Exception as e:
                        log.warning(f"[HPM] Full re-import failed for '{tag}': {e}")

                if reloaded:
                    _hot_reload_registry(cfg_mgr, log)
                    _invalidate_all_caches()
                    return jsonify({"ok": True, "message": f"Module '{tag}' reloaded ({reloaded_info})."})
                else:
                    return jsonify({"ok": False, "error": f"Module '{tag}' could not be reloaded — not found or main.py missing."}), 400

        except Exception as e:
            log.error(f"[HPM] Single module hot-reload error for {pkg_id}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
