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

    @app.route("/api/packages/<pkg_id>/readme", methods=["GET"])
    @login_required
    def api_get_package_readme(pkg_id):
        """Retrieve the README.md content for a given HPM package."""
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            pkg = registry.get(pkg_id)
            if not pkg:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404
            
            install_path = pkg.get("install_path")
            if not install_path or not os.path.exists(install_path):
                return jsonify({"ok": False, "error": "Install path not found"}), 404
                
            manifest = registry.get_manifest(pkg_id) or {}
            readme_file = manifest.get("readme", "README.md")
            
            readme_path = os.path.join(install_path, readme_file)
            if not os.path.exists(readme_path):
                # Fallback to case-insensitive or different common names if not found
                for fallback in ["README.md", "docs.md", "README.txt", "readme.md"]:
                    fb_path = os.path.join(install_path, fallback)
                    if os.path.exists(fb_path):
                        readme_path = fb_path
                        break

            if not os.path.exists(readme_path):
                return jsonify({"ok": False, "error": "No documentation file found for this package."}), 404
                
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            return jsonify({"ok": True, "content": content})
        except Exception as e:
            log.error(f"[HPM] GET /api/packages/{pkg_id}/readme error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/<pkg_id>/verify", methods=["GET"])
    @login_required
    def api_verify_package(pkg_id):
        """Verify the integrity of an installed package using file hashes."""
        try:
            import hashlib
            registry, _, _ = _get_hpm_components(_hecos_src)
            pkg = registry.get(pkg_id)
            if not pkg:
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404
            
            manifest = registry.get_manifest(pkg_id) or {}
            file_hashes = manifest.get("file_hashes", {})
            if not file_hashes:
                return jsonify({"ok": True, "status": "unverified", "message": "No file hashes available in manifest"})
                
            install_path = pkg.get("install_path")
            if not install_path or not os.path.exists(install_path):
                return jsonify({"ok": False, "error": "Install path missing or not found"}), 404
                
            missing = []
            modified = []
            
            for rel_path, expected_hash in file_hashes.items():
                # Prevent path traversal in relative path
                safe_rel = rel_path.replace("\\", "/").lstrip("/")
                abs_path = os.path.join(install_path, safe_rel)
                
                if not os.path.exists(abs_path):
                    missing.append(rel_path)
                    continue
                    
                sha256 = hashlib.sha256()
                with open(abs_path, "rb") as f:
                    while chunk := f.read(8192):
                        sha256.update(chunk)
                        
                if sha256.hexdigest().lower() != expected_hash.lower():
                    modified.append(rel_path)
                    
            if not missing and not modified:
                return jsonify({"ok": True, "status": "valid", "message": "All files verified successfully"})
            else:
                return jsonify({
                    "ok": True, 
                    "status": "invalid", 
                    "missing_files": missing,
                    "modified_files": modified,
                    "message": f"Verification failed: {len(missing)} missing, {len(modified)} modified"
                })
        except Exception as e:
            log.error(f"[HPM] GET /api/packages/{pkg_id}/verify error: {e}")
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
                return jsonify({"ok": True, "message": f"Module '{tag}' reloaded successfully."})
            else:
                return jsonify({"ok": False, "error": f"Module '{tag}' is not active or could not be restarted."}), 400

        except Exception as e:
            log.error(f"[HPM] Single module hot-reload error for {pkg_id}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
