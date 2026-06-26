"""
routes_packages_manage.py
─────────────────────────────────────────────────────────────────────────────
Get, update status, and delete packages.
"""
from __future__ import annotations
from flask import jsonify, request
from flask_login import login_required

from hecos.modules.web_ui.routes_packages_helpers import (
    _get_hpm_components,
    _refresh_jinja_loader,
    _hpm_event_broadcast
)

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
            ok = registry.set_status(pkg_id, status)
            if ok:
                # If disabling, also disable all associated widgets in config to force UI refresh
                if status == "disabled":
                    snap = pkg.get("manifest_snapshot", {})
                    if isinstance(snap, str):
                        import json
                        try: snap = json.loads(snap)
                        except: snap = {}
                    widgets_modified = 0
                    tag = snap.get("tag")
                    if tag:
                        cfg_mgr.set(False, "plugins", tag, "enabled")
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
                    # Re-enable the widget in the config so it can appear again
                    snap = pkg.get("manifest_snapshot", {})
                    if isinstance(snap, str):
                        import json
                        try: snap = json.loads(snap)
                        except: snap = {}
                    widgets_modified = 0
                    tag = snap.get("tag")
                    if tag:
                        cfg_mgr.set(True, "plugins", tag, "enabled")
                        widgets_modified += 1
                    for w in snap.get("widgets", []):
                        ext_id = w.get("id")
                        if ext_id:
                            cfg_mgr.set(True, "widgets", "per_widget", ext_id, "enabled")
                            # We also turn it back on for the sidebar (visible=True), 
                            # but we leave room_visible untouched to respect user preference
                            cfg_mgr.set(True, "widgets", "per_widget", ext_id, "visible")
                            widgets_modified += 1
                    if widgets_modified > 0:
                        cfg_mgr.save()

                _hpm_event_broadcast("hpm:package_status_changed", {
                    "id": pkg_id, "status": status
                })
            return jsonify({"ok": ok, "id": pkg_id, "status": status})
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
