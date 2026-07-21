"""
routes_packages_install.py
─────────────────────────────────────────────────────────────────────────────
Install packages.
"""
from __future__ import annotations
import os
from flask import jsonify, request
from flask_login import login_required

from hecos.modules.web_ui.routes_packages_helpers import (
    _get_hpm_components,
    _refresh_jinja_loader,
    _hpm_event_broadcast,
    add_to_pending_restart,
    _PENDING_RESTART_TYPES,
)

def _invalidate_all_caches():
    """Invalidate packages and widgets caches after any install/uninstall event."""
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
    # Reload slash commands registry so newly installed modules appear immediately
    try:
        from hecos.core.commands.registry import get_registry
        get_registry(reload=True)
    except Exception:
        pass

def register_install_routes(app, _hecos_src: str, cfg_mgr, log):

    @app.route("/api/packages/install", methods=["POST"])
    @login_required
    def api_install_package():
        """
        Install a .hpkg package uploaded as multipart/form-data.
        Field name: 'hpkg_file'
        """
        if "hpkg_file" not in request.files:
            return jsonify({"ok": False, "error": "No 'hpkg_file' in request"}), 400

        hpkg_file = request.files["hpkg_file"]
        if not hpkg_file.filename:
            return jsonify({"ok": False, "error": "No file selected"}), 400

        # Read bytes immediately (before threading)
        hpkg_bytes = hpkg_file.read()
        log.info(f"[HPM] Install requested: {hpkg_file.filename} ({len(hpkg_bytes)} bytes)")

        allow_unsigned_str = request.form.get("allow_unsigned", "false").lower()
        allow_unsigned = allow_unsigned_str in ("true", "1", "yes")

        skip_dep_str = request.form.get("skip_dep_check", "false").lower()
        skip_dep = skip_dep_str in ("true", "1", "yes")

        try:
            registry, installer, _ = _get_hpm_components(_hecos_src)
            result = installer.install_bytes(hpkg_bytes, require_signature=not allow_unsigned, skip_dep_check=skip_dep)

            if result.success:
                # ── Clear Config Panel Cache ──
                try:
                    from hecos.modules.web_ui.routes_config_core import clear_hpm_panel_cache
                    clear_hpm_panel_cache()
                except ImportError:
                    pass

                # ── Hot-patch Jinja loader so widget templates are found immediately ──
                _refresh_jinja_loader(app)

                # ── Re-discover extensions so new widgets appear without restart ──
                try:
                    from hecos.core.system.extension_loader import discover_webui_extensions, load_eager_extensions
                    webui_ext_dir = os.path.join(_hecos_src, "modules", "web_ui")
                    discover_webui_extensions(webui_ext_dir)
                    load_eager_extensions(app, "WEB_UI")
                    log.info(f"[HPM:Routes] Extensions re-discovered after install.")
                except Exception as _ext_e:
                    log.warning(f"[HPM:Routes] Extension re-discovery failed: {_ext_e}")

                # ── Force-enable the package in the LIVE cfg_mgr ──
                # Only relevant for plugin-namespace types. Widgets (widget-only),
                # personas and themes don't have a runtime `plugins.TAG` entry.
                _PLUGIN_NS_TYPES = {"core_module", "plugin", "module", "extension", "app", "skill_pack"}
                try:
                    import json as _json, zipfile as _zf, io as _io
                    _zb = _zf.ZipFile(_io.BytesIO(hpkg_bytes))
                    _raw_manifest = None
                    for _name in _zb.namelist():
                        if _name.endswith("hpkg_manifest.toml"):
                            _raw_manifest = _zb.read(_name)
                            break
                    if _raw_manifest:
                        try:
                            import tomllib as _toml
                        except ImportError:
                            import tomli as _toml
                        _mdict = _toml.loads(_raw_manifest.decode("utf-8"))
                        _pkg_type = _mdict.get("type", "plugin")
                        _tag = _mdict.get("tag", "")
                        if _tag and _pkg_type in _PLUGIN_NS_TYPES:
                            pass # HPM packages manage their own status in the SQLite DB.
                        for _w in _mdict.get("widgets", []):
                            _wid = _w.get("id", "")
                            if _wid:
                                cfg_mgr.set(True, "widgets", "per_widget", _wid, "enabled")
                                # XOR default: widgets start in Control Room, not sidebar
                                cfg_mgr.set(False, "widgets", "per_widget", _wid, "visible")
                                cfg_mgr.set(True, "widgets", "per_widget", _wid, "room_visible")
                        if _mdict.get("widgets"):
                            cfg_mgr.save()
                except Exception as _ce:
                    log.warning(f"[HPM] Could not force-enable in live cfg_mgr: {_ce}")

                _hpm_event_broadcast("hpm:package_installed", {"id": result.package_id})
                _invalidate_all_caches()

                # ── Hot-reload capability registry with live config ──
                try:
                    from hecos.core.system import module_loader
                    module_loader.update_capability_registry(cfg_mgr.config, debug_log=False)
                    log.info(f"[HPM] Capability registry hot-reloaded after install of '{result.package_id}'")
                except Exception as _reg_e:
                    log.warning(f"[HPM] Capability registry reload failed: {_reg_e}")

                # ── Reload slash command registry ──
                try:
                    from hecos.core.commands.registry import get_registry
                    get_registry(reload=True)
                    log.info(f"[HPM] Command registry reloaded after install of '{result.package_id}'")
                except Exception as _cr_e:
                    log.warning(f"[HPM] Command registry reload failed: {_cr_e}")

                pkg_meta = registry.get(result.package_id) or {}
                snap = pkg_meta.get("manifest_snapshot", {})
                if isinstance(snap, str):
                    try:
                        import json as _j
                        snap = _j.loads(snap)
                    except: snap = {}

                # ── Dynamically load API routes for the newly installed package ──
                try:
                    cp = snap.get("config_panel") or {}
                    api_routes_file = cp.get("api_routes_file")
                    if api_routes_file:
                        plugin_id = result.package_id
                        install_path = pkg_meta.get("install_path")
                        if install_path:
                            abs_route_path = os.path.join(install_path, api_routes_file)
                            if os.path.isfile(abs_route_path):
                                import importlib.util
                                spec = importlib.util.spec_from_file_location(f"plugin_routes_{plugin_id}", abs_route_path)
                                mod = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(mod)
                                if hasattr(mod, 'init_plugin_routes'):
                                    # Pass hecos_root correctly. We use _hecos_src root dir.
                                    mod.init_plugin_routes(app, cfg_mgr, os.path.dirname(_hecos_src) if _hecos_src.endswith("hecos") else _hecos_src, log)
                                    log.info(f"[HPM:Routes] Dynamically registered API routes for newly installed '{plugin_id}'")
                except Exception as _route_e:
                    log.error(f"[HPM:Routes] Failed to dynamically load routes for '{result.package_id}': {_route_e}")

                panel_id = (snap.get("config_panel") or {}).get("tab_id") or result.package_id

                # ── Determine if this package requires a restart ──────────────────
                pkg_type = pkg_meta.get("type", "plugin")
                has_api_routes = bool((snap.get("config_panel") or {}).get("api_routes_file"))
                needs_restart = pkg_type in _PENDING_RESTART_TYPES or has_api_routes
                if needs_restart:
                    add_to_pending_restart(result.package_id)
                    _invalidate_all_caches()  # ensure requires_restart is reflected in fresh cache
                # ─────────────────────────────────────────────────────────────────

                response = {
                    "ok": True,
                    "id": result.package_id,
                    "name": pkg_meta.get("name", result.package_id),
                    "type": pkg_meta.get("type", ""),
                    "install_path": pkg_meta.get("install_path", ""),
                    "config_panel": panel_id if snap.get("config_panel") else "",
                    "warnings": result.warnings,
                    "requires_restart": needs_restart,
                    "is_update": getattr(result, "is_update", False)
                }
                if result.dep_report and result.dep_report.has_issues:
                    response["dep_issues"] = result.dep_report.summary
                if result.dep_report and result.dep_report.missing_optional:
                    response["optional_missing"] = result.dep_report.missing_optional
                return jsonify(response)
            else:
                is_signature_error = "signature" in result.error.lower()
                missing = result.dep_report.missing_packages if result.dep_report else []
                return jsonify({
                    "ok": False,
                    "error": result.error,
                    "signature_error": is_signature_error,
                    "missing_deps": missing,
                }), 400

        except Exception as e:
            log.error(f"[HPM] Install error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/install/batch", methods=["POST"])
    @login_required
    def api_install_packages_batch():
        """
        Install multiple .hpkg packages in a single request.
        Field name: 'hpkg_files[]'  (multipart, multiple files)
        Returns: { ok, total, succeeded, failed, results: [{filename, ok, id, name, error, warnings}, ...] }
        """
        files = request.files.getlist("hpkg_files[]")
        if not files:
            return jsonify({"ok": False, "error": "No 'hpkg_files[]' in request"}), 400

        allow_unsigned_str = request.form.get("allow_unsigned", "false").lower()
        allow_unsigned = allow_unsigned_str in ("true", "1", "yes")
        skip_dep_str = request.form.get("skip_dep_check", "false").lower()
        skip_dep = skip_dep_str in ("true", "1", "yes")

        registry, installer, _ = _get_hpm_components(_hecos_src)

        results = []
        succeeded = 0
        failed = 0

        for hpkg_file in files:
            filename = hpkg_file.filename or "unknown.hpkg"
            if not (filename.endswith(".hpkg") or filename.endswith(".zip")):
                results.append({"filename": filename, "ok": False, "error": "Not a .hpkg file"})
                failed += 1
                continue

            try:
                hpkg_bytes = hpkg_file.read()
                log.info(f"[HPM:Batch] Installing: {filename} ({len(hpkg_bytes)} bytes)")
                result = installer.install_bytes(hpkg_bytes, require_signature=not allow_unsigned, skip_dep_check=skip_dep)

                if result.success:
                    # ── Hot-patch Jinja & re-discover extensions ──
                    _refresh_jinja_loader(app)
                    try:
                        from hecos.core.system.extension_loader import discover_webui_extensions, load_eager_extensions
                        webui_ext_dir = os.path.join(_hecos_src, "modules", "web_ui")
                        discover_webui_extensions(webui_ext_dir)
                        load_eager_extensions(app, "WEB_UI")
                    except Exception as _ext_e:
                        log.warning(f"[HPM:Batch] Extension re-discovery failed for {filename}: {_ext_e}")

                    # ── Clear config panel cache ──
                    try:
                        from hecos.modules.web_ui.routes_config_core import clear_hpm_panel_cache
                        clear_hpm_panel_cache()
                    except ImportError:
                        pass

                    # ── Force-enable plugin/widgets in live cfg_mgr ──
                    _PLUGIN_NS_TYPES = {"core_module", "plugin", "module", "extension", "app", "skill_pack"}
                    try:
                        import zipfile as _zf, io as _io
                        try:
                            import tomllib as _toml
                        except ImportError:
                            import tomli as _toml
                        _zb = _zf.ZipFile(_io.BytesIO(hpkg_bytes))
                        _raw_manifest = None
                        for _name in _zb.namelist():
                            if _name.endswith("hpkg_manifest.toml"):
                                _raw_manifest = _zb.read(_name)
                                break
                        if _raw_manifest:
                            _mdict = _toml.loads(_raw_manifest.decode("utf-8"))
                            for _w in _mdict.get("widgets", []):
                                _wid = _w.get("id", "")
                                if _wid:
                                    cfg_mgr.set(True, "widgets", "per_widget", _wid, "enabled")
                                    cfg_mgr.set(False, "widgets", "per_widget", _wid, "visible")
                                    cfg_mgr.set(True, "widgets", "per_widget", _wid, "room_visible")
                            if _mdict.get("widgets"):
                                cfg_mgr.save()
                    except Exception as _ce:
                        log.warning(f"[HPM:Batch] Could not force-enable in live cfg_mgr for {filename}: {_ce}")

                    pkg_meta = registry.get(result.package_id) or {}
                    snap = pkg_meta.get("manifest_snapshot", {})
                    if isinstance(snap, str):
                        try:
                            import json as _j
                            snap = _j.loads(snap)
                        except:
                            snap = {}
                    panel_id = (snap.get("config_panel") or {}).get("tab_id") or result.package_id

                    entry = {
                        "filename": filename,
                        "ok": True,
                        "id": result.package_id,
                        "name": pkg_meta.get("name", result.package_id),
                        "type": pkg_meta.get("type", ""),
                        "install_path": pkg_meta.get("install_path", ""),
                        "config_panel": panel_id if snap.get("config_panel") else "",
                        "warnings": result.warnings or [],
                        "is_update": getattr(result, "is_update", False),
                    }
                    if result.dep_report and result.dep_report.has_issues:
                        entry["dep_issues"] = result.dep_report.summary
                    results.append(entry)
                    succeeded += 1

                    _hpm_event_broadcast("hpm:package_installed", {"id": result.package_id})

                else:
                    results.append({
                        "filename": filename,
                        "ok": False,
                        "error": result.error,
                        "signature_error": "signature" in (result.error or "").lower(),
                        "missing_deps": result.dep_report.missing_packages if result.dep_report else [],
                    })
                    failed += 1

            except Exception as e:
                log.error(f"[HPM:Batch] Error installing {filename}: {e}")
                results.append({"filename": filename, "ok": False, "error": str(e)})
                failed += 1

        _invalidate_all_caches()
        if succeeded > 0:
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
