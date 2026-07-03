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

def register_manage_routes(app, _hecos_src: str, cfg_mgr, log):

    @app.route("/api/packages/<pkg_id>", methods=["GET"])
    @login_required
    def api_get_package(pkg_id):
        """Return full details of a specific installed package."""
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            pkg = registry.get(pkg_id)
            if not pkg:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404
            return jsonify({"ok": True, "package": pkg})
        except Exception as e:
            log.error(f"[HPM] GET /api/packages/{pkg_id} error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/<pkg_id>/manifest", methods=["GET"])
    @login_required
    def api_get_package_manifest(pkg_id):
        """Return the full hpkg_manifest snapshot for a package."""
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            manifest = registry.get_manifest(pkg_id)
            if manifest is None:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404
            return jsonify({"ok": True, "manifest": manifest})
        except Exception as e:
            log.error(f"[HPM] GET /api/packages/{pkg_id}/manifest error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/<pkg_id>/capabilities", methods=["GET"])
    @login_required
    def api_get_package_capabilities(pkg_id):
        """Return the capability card structure for a package."""
        try:
            from hecos.core.system.capability_inspector import build_card
            from dataclasses import asdict
            
            # Check if auto-introspect is enabled in config
            cfg = cfg_mgr.config if cfg_mgr else {}
            introspect = (
                cfg.get("hpm", {}).get("auto_introspect", False)
                if isinstance(cfg, dict) else False
            )
            
            card = build_card(pkg_id, introspect=introspect)
            if card is None:
                return jsonify({"ok": False, "error": f"Capabilities for '{pkg_id}' not found"}), 404
                
            return jsonify({"ok": True, "card": asdict(card)})
        except Exception as e:
            log.error(f"[HPM] GET /api/packages/{pkg_id}/capabilities error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/<pkg_id>/update", methods=["POST"])
    @login_required
    def api_update_package(pkg_id):
        """
        Update an installed package by uploading a new .hpkg file.
        Preserves the original install date and saves the previous version
        in the registry. Config defaults are NOT overwritten (only missing
        keys are injected), so the user's customization is preserved.

        Field name: 'hpkg_file'
        """
        from hecos.modules.web_ui.routes_packages_helpers import _refresh_jinja_loader
        from hecos.modules.web_ui.routes_packages_install import register_install_routes  # noqa
        # The install route already handles everything correctly because
        # registry.register() now detects existing packages and does an UPDATE.
        # We just delegate to the same install logic.
        if "hpkg_file" not in request.files:
            return jsonify({"ok": False, "error": "No 'hpkg_file' in request"}), 400

        hpkg_file = request.files["hpkg_file"]
        if not hpkg_file.filename:
            return jsonify({"ok": False, "error": "No file selected"}), 400

        hpkg_bytes = hpkg_file.read()
        allow_unsigned_str = request.form.get("allow_unsigned", "false").lower()
        allow_unsigned = allow_unsigned_str in ("true", "1", "yes")

        log.info(f"[HPM] Update requested for '{pkg_id}': {hpkg_file.filename} ({len(hpkg_bytes)} bytes)")

        try:
            registry, installer, _ = _get_hpm_components(_hecos_src)

            # Verify the uploaded package matches the expected id
            import io, zipfile as _zf
            try:
                import tomllib as _toml
            except ImportError:
                import tomli as _toml
            with _zf.ZipFile(io.BytesIO(hpkg_bytes)) as zf:
                raw = None
                for name in zf.namelist():
                    if name.endswith("hpkg_manifest.toml"):
                        raw = zf.read(name)
                        break
                if not raw:
                    return jsonify({"ok": False, "error": "No manifest found in package"}), 400
                mdict = _toml.loads(raw.decode("utf-8"))
                if mdict.get("id") != pkg_id:
                    return jsonify({
                        "ok": False,
                        "error": f"Package ID mismatch: expected '{pkg_id}', got '{mdict.get('id')}'"
                    }), 400

            result = installer.install_bytes(hpkg_bytes, require_signature=not allow_unsigned)

            if result.success:
                _refresh_jinja_loader(app)
                try:
                    from hecos.core.system.extension_loader import discover_webui_extensions, load_eager_extensions
                    webui_ext_dir = os.path.join(_hecos_src, "modules", "web_ui")
                    discover_webui_extensions(webui_ext_dir)
                    load_eager_extensions(app, "WEB_UI")
                except Exception as _ext_e:
                    log.warning(f"[HPM:Routes] Extension re-discovery after update failed: {_ext_e}")

                _hpm_event_broadcast("hpm:package_updated", {"id": pkg_id})
                _invalidate_all_caches()
                response = {
                    "ok": True,
                    "id": pkg_id,
                    "version": mdict.get("version"),
                    "warnings": result.warnings,
                }
                if result.dep_report and result.dep_report.missing_optional:
                    response["optional_missing"] = result.dep_report.missing_optional
                return jsonify(response)
            else:
                return jsonify({"ok": False, "error": result.error}), 400

        except Exception as e:
            log.error(f"[HPM] Update error for '{pkg_id}': {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

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
                    widgets_modified = 0
                    cfg_mgr.set(False, "plugins", pkg_tag, "enabled")
                    widgets_modified += 1
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
                    cfg_mgr.set(True, "plugins", pkg_tag, "enabled")
                    widgets_modified += 1
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
            return jsonify({"ok": ok, "id": pkg_id, "status": status, "tag": pkg_tag, "panel_id": panel_id})
        except Exception as e:
            log.error(f"[HPM] PATCH /api/packages/{pkg_id}/status error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/<pkg_id>", methods=["DELETE"])
    @login_required
    def api_uninstall_package(pkg_id):
        """Uninstall a package by its id."""
        try:
            registry, _, uninstaller = _get_hpm_components(_hecos_src)
            pkg = registry.get(pkg_id)
            if not pkg:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not installed"}), 404

            # Extract widget IDs before uninstall deletes the package record
            snap = pkg.get("manifest_snapshot", {})
            if isinstance(snap, str):
                import json
                try: snap = json.loads(snap)
                except: snap = {}
            widget_ids_to_hide = [w.get("id") for w in snap.get("widgets", []) if w.get("id")]

            result = uninstaller.uninstall(pkg_id)

            if result.success:
                # ── Purge extensions from the in-memory registry immediately ──
                try:
                    from hecos.core.system.extension_loader import purge_extension
                    
                    # The package was removed from DB by uninstaller.
                    # We know exactly which widgets it had from the manifest snapshot.
                    for ext_id in widget_ids_to_hide:
                        purge_extension(ext_id, "WEB_UI")
                        log.info(f"[HPM] Purged extension from registry: {ext_id}")
                    
                    # Also update the Jinja loader to remove stale paths
                    _refresh_jinja_loader(app)

                    # ── Clear Config Panel Cache ──
                    try:
                        from hecos.modules.web_ui.routes_config_core import clear_hpm_panel_cache
                        clear_hpm_panel_cache()
                    except ImportError:
                        pass

                    # Forcefully hide any uninstalled widgets from the config (mimic Widget Layout "off")
                    for ext_id in widget_ids_to_hide:
                        cfg_mgr.set(False, "widgets", "per_widget", ext_id, "enabled")
                        cfg_mgr.set(False, "widgets", "per_widget", ext_id, "visible")
                        cfg_mgr.set(False, "widgets", "per_widget", ext_id, "room_visible")
                    tag = snap.get("tag")
                    if tag:
                        cfg_mgr.set(False, "plugins", tag, "enabled")
                    if widget_ids_to_hide or tag:
                        cfg_mgr.save()

                except Exception as _purge_e:
                    log.warning(f"[HPM] Extension purge failed: {_purge_e}")

                _hpm_event_broadcast("hpm:package_uninstalled", {"id": pkg_id})
                _invalidate_all_caches()
                return jsonify({
                    "ok": True,
                    "id": pkg_id,
                    "removed_files_count": len(result.removed_files),
                    "skipped_files": result.skipped_files,
                })
            else:
                return jsonify({
                    "ok": False,
                    "error": result.error,
                }), 500

        except Exception as e:
            log.error(f"[HPM] DELETE /api/packages/{pkg_id} error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/hpm/settings/sounds", methods=["GET"])
    @login_required
    def api_hpm_settings_sounds():
        """Lists available sound files in assets/sounds."""
        sounds_dir = os.path.abspath(os.path.join(_hecos_src, "assets", "sounds"))
        try:
            os.makedirs(sounds_dir, exist_ok=True)
            files = [
                f for f in os.listdir(sounds_dir)
                if f.lower().endswith((".mp3", ".wav", ".ogg", ".aac"))
            ]
            files.sort()
            return jsonify({"ok": True, "sounds": files, "sounds_dir": sounds_dir})
        except Exception as e:
            log.error(f"[HPM] GET /api/hpm/settings/sounds error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
