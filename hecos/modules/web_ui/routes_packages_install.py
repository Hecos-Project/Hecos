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
    _hpm_event_broadcast
)

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

        # Read bypass flag
        allow_unsigned_str = request.form.get("allow_unsigned", "false").lower()
        allow_unsigned = allow_unsigned_str in ("true", "1", "yes")

        try:
            registry, installer, _ = _get_hpm_components(_hecos_src)
            result = installer.install_bytes(hpkg_bytes, require_signature=not allow_unsigned)

            if result.success:
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
                            # Force enable — overwrite regardless of previous state
                            cfg_mgr.set(True, "plugins", _tag, "enabled")
                        for _w in _mdict.get("widgets", []):
                            _wid = _w.get("id", "")
                            if _wid:
                                cfg_mgr.set(True, "widgets", "per_widget", _wid, "enabled")
                                cfg_mgr.set(True, "widgets", "per_widget", _wid, "visible")
                        if (_tag and _pkg_type in _PLUGIN_NS_TYPES) or _mdict.get("widgets"):
                            cfg_mgr.save()
                            log.info(f"[HPM] Force-enabled '{_tag}' in live cfg_mgr after install.")
                except Exception as _ce:
                    log.warning(f"[HPM] Could not force-enable in live cfg_mgr: {_ce}")

                _hpm_event_broadcast("hpm:package_installed", {"id": result.package_id})

                response = {
                    "ok": True,
                    "id": result.package_id,
                    "warnings": result.warnings,
                }
                if result.dep_report and result.dep_report.has_issues:
                    response["dep_issues"] = result.dep_report.summary
                if result.dep_report and result.dep_report.missing_optional:
                    response["optional_missing"] = result.dep_report.missing_optional
                return jsonify(response)
            else:
                is_signature_error = "signature" in result.error.lower()
                return jsonify({
                    "ok": False,
                    "error": result.error,
                    "signature_error": is_signature_error
                }), 400

        except Exception as e:
            log.error(f"[HPM] Install error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
