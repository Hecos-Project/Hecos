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

def register_manage_config_routes(app, _hecos_src: str, cfg_mgr, log):
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

