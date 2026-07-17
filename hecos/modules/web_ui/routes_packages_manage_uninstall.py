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
from hecos.modules.web_ui.routes_packages_manage_status import _invalidate_all_caches

def register_manage_uninstall_routes(app, _hecos_src: str, cfg_mgr, log):
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
            
            # ── Stop the module subprocess to release file locks ──
            tag = snap.get("tag")
            if tag:
                try:
                    from hecos.core.module_bus import get_bus
                    get_bus().stop_plugin(tag.upper())
                    log.info(f"[HPM] Stopped running module '{tag}' before uninstall.")
                except Exception as _stop_e:
                    log.warning(f"[HPM] Could not stop module '{tag}' before uninstall: {_stop_e}")
                # Hard-kill any surviving runner processes for this package (Windows safety)
                try:
                    import psutil, time
                    install_path = pkg.get("install_path", "")
                    killed = 0
                    for proc in psutil.process_iter(['pid', 'cmdline']):
                        try:
                            cmd = ' '.join(proc.info.get('cmdline') or [])
                            if install_path and install_path in cmd:
                                proc.kill()
                                killed += 1
                            elif 'hecos_sdk.runner' in cmd:
                                proc.kill()
                                killed += 1
                        except Exception:
                            pass
                    if killed:
                        log.info(f"[HPM] Hard-killed {killed} residual runner process(es) for '{pkg_id}'.")
                    time.sleep(1.0)  # Give Windows time to release file handles
                except ImportError:
                    import time; time.sleep(1.0)
                except Exception as _kill_e:
                    log.warning(f"[HPM] Hard-kill sweep failed: {_kill_e}")

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
                    if widget_ids_to_hide:
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

    @app.route("/api/packages/uninstall/batch", methods=["POST"])
    @login_required
    def api_uninstall_packages_batch():
        """
        Uninstall multiple packages by ID.
        Body: { "ids": ["pkg1", "pkg2", ...] }
        Returns: { ok, total, succeeded, failed, results: [{id, ok, removed_files_count, error}, ...] }
        """
        data = request.get_json(silent=True) or {}
        ids = data.get("ids", [])
        if not isinstance(ids, list) or not ids:
            return jsonify({"ok": False, "error": "Missing or empty 'ids' list"}), 400

        registry, _, uninstaller = _get_hpm_components(_hecos_src)

        results = []
        succeeded = 0
        failed = 0
        any_cache_invalidate = False

        for pkg_id in ids:
            try:
                pkg = registry.get(pkg_id)
                if not pkg:
                    results.append({"id": pkg_id, "ok": False, "error": "Not installed"})
                    failed += 1
                    continue

                snap = pkg.get("manifest_snapshot", {})
                if isinstance(snap, str):
                    import json
                    try: snap = json.loads(snap)
                    except: snap = {}
                widget_ids_to_hide = [w.get("id") for w in snap.get("widgets", []) if w.get("id")]

                log.info(f"[HPM:Batch] Uninstalling: {pkg_id}")
                result = uninstaller.uninstall(pkg_id)

                if result.success:
                    any_cache_invalidate = True
                    try:
                        from hecos.core.system.extension_loader import purge_extension
                        for ext_id in widget_ids_to_hide:
                            purge_extension(ext_id, "WEB_UI")
                        _refresh_jinja_loader(app)

                        for ext_id in widget_ids_to_hide:
                            cfg_mgr.set(False, "widgets", "per_widget", ext_id, "enabled")
                            cfg_mgr.set(False, "widgets", "per_widget", ext_id, "visible")
                            cfg_mgr.set(False, "widgets", "per_widget", ext_id, "room_visible")
                        if widget_ids_to_hide:
                            cfg_mgr.save()
                    except Exception as _purge_e:
                        log.warning(f"[HPM:Batch] Extension purge failed for {pkg_id}: {_purge_e}")

                    _hpm_event_broadcast("hpm:package_uninstalled", {"id": pkg_id})
                    results.append({
                        "id": pkg_id,
                        "ok": True,
                        "removed_files_count": len(result.removed_files),
                        "skipped_files": result.skipped_files,
                    })
                    succeeded += 1
                else:
                    results.append({
                        "id": pkg_id,
                        "ok": False,
                        "error": result.error,
                    })
                    failed += 1
            except Exception as e:
                log.error(f"[HPM:Batch] DELETE {pkg_id} error: {e}")
                results.append({"id": pkg_id, "ok": False, "error": str(e)})
                failed += 1

        if any_cache_invalidate:
            _invalidate_all_caches()
            _hot_reload_registry(cfg_mgr, log)
            try:
                from hecos.modules.web_ui.routes_config_core import clear_hpm_panel_cache
                clear_hpm_panel_cache()
            except ImportError:
                pass

        return jsonify({
            "ok": True,
            "total": len(results),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        })


