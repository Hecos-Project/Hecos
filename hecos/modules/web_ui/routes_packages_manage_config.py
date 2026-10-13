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
                
                from hecos.modules.web_ui.routes_packages_helpers import _PENDING_RESTART_TYPES, add_to_pending_restart
                pkg_type = mdict.get("type", "plugin")
                has_api_routes = bool(mdict.get("api_routes_file") or (mdict.get("config_panel") or {}).get("api_routes_file"))
                needs_restart = pkg_type in _PENDING_RESTART_TYPES or has_api_routes
                if needs_restart:
                    add_to_pending_restart(pkg_id)

                response = {
                    "ok": True,
                    "id": pkg_id,
                    "version": mdict.get("version"),
                    "warnings": result.warnings,
                    "requires_restart": needs_restart,
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

    @app.route("/api/hpm/settings/reset_cache", methods=["POST"])
    @login_required
    def api_hpm_settings_reset_cache():
        try:
            db_path = os.path.join(cfg_mgr.config.get("hpm_data_dir", os.path.join(_hecos_src, "data")), "packages.db")
            if not os.path.exists(db_path):
                # Fallback to alternative paths if needed
                db_path = os.path.join(_hecos_src, "data", "packages.db")
            
            if os.path.exists(db_path):
                import sqlite3
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT id, install_path FROM packages")
                rows = c.fetchall()
                import json
                updated_count = 0
                for row in rows:
                    if row[1]:
                        manifest_file = os.path.join(_hecos_src, row[1], "manifest.json")
                        if os.path.exists(manifest_file):
                            try:
                                with open(manifest_file, 'r', encoding='utf-8') as f:
                                    md = json.load(f)
                                c.execute("UPDATE packages SET manifest_snapshot = ? WHERE id = ?", (json.dumps(md), row[0]))
                                updated_count += 1
                            except Exception:
                                pass
                conn.commit()
                conn.close()
                log.info("[HPM] Packages manifest cache (DB) cleared.")
                _invalidate_all_caches()
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "Database not found."}), 404
        except Exception as e:
            log.error(f"[HPM] POST /api/hpm/settings/reset_cache error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/hpm/settings/repositories", methods=["GET"])
    @login_required
    def api_hpm_get_repositories():
        """Returns the list of configured package repositories and the active one."""
        default_repo = "https://hecos-project.github.io/store/index.json"
        repos = []
        active = default_repo
        try:
            if cfg_mgr:
                hpm_cfg = cfg_mgr.get("hpm") or {}
                if isinstance(hpm_cfg, dict):
                    repos = list(hpm_cfg.get("repositories") or [])
                    active = hpm_cfg.get("store_catalog_url") or default_repo
                elif hasattr(hpm_cfg, "repositories"):
                    repos = list(getattr(hpm_cfg, "repositories", []) or [])
                    active = getattr(hpm_cfg, "store_catalog_url", default_repo) or default_repo

            if not repos or not isinstance(repos, list):
                repos = [default_repo]
            if default_repo not in repos:
                repos.insert(0, default_repo)

            if not active or active not in repos:
                active = repos[0]

            return jsonify({
                "ok": True,
                "repositories": repos,
                "active_repository": active
            })
        except Exception as e:
            log.error(f"[HPM] GET /api/hpm/settings/repositories error: {e}")
            return jsonify({"ok": False, "error": str(e), "repositories": [default_repo], "active_repository": default_repo}), 500

    @app.route("/api/hpm/settings/repositories", methods=["POST"])
    @login_required
    def api_hpm_set_repositories():
        """Updates the list of configured repositories and optionally the active repository."""
        default_repo = "https://hecos-project.github.io/store/index.json"
        try:
            data = request.get_json(silent=True) or {}
            raw_repos = data.get("repositories", [])
            active_repo = (data.get("active_repository") or "").strip()

            if isinstance(raw_repos, str):
                lines = [l.strip() for l in raw_repos.replace(",", "\n").splitlines()]
            elif isinstance(raw_repos, list):
                lines = [str(l).strip() for l in raw_repos]
            else:
                lines = []

            cleaned = []
            for l in lines:
                if l and not l.startswith("#") and l not in cleaned:
                    cleaned.append(l)

            if not cleaned:
                cleaned = [default_repo]

            if not active_repo or active_repo not in cleaned:
                active_repo = cleaned[0]

            if cfg_mgr:
                if "hpm" not in cfg_mgr.config or not isinstance(cfg_mgr.config["hpm"], dict):
                    cfg_mgr.config["hpm"] = {}
                cfg_mgr.config["hpm"]["repositories"] = cleaned
                cfg_mgr.config["hpm"]["store_catalog_url"] = active_repo
                cfg_mgr.save()

            log.info(f"[HPM] Repositories updated ({len(cleaned)} repos, active: {active_repo})")
            return jsonify({
                "ok": True,
                "repositories": cleaned,
                "active_repository": active_repo
            })
        except Exception as e:
            log.error(f"[HPM] POST /api/hpm/settings/repositories error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/hpm/settings/active_repository", methods=["POST"])
    @login_required
    def api_hpm_set_active_repository():
        """Changes the currently active repository URL."""
        try:
            data = request.get_json(silent=True) or {}
            active_repo = (data.get("active_repository") or "").strip()
            if not active_repo:
                return jsonify({"ok": False, "error": "active_repository is required"}), 400

            if cfg_mgr:
                if "hpm" not in cfg_mgr.config or not isinstance(cfg_mgr.config["hpm"], dict):
                    cfg_mgr.config["hpm"] = {}
                repos = cfg_mgr.config["hpm"].get("repositories", [])
                if not isinstance(repos, list):
                    repos = []
                if active_repo not in repos:
                    repos.append(active_repo)
                    cfg_mgr.config["hpm"]["repositories"] = repos

                cfg_mgr.config["hpm"]["store_catalog_url"] = active_repo
                cfg_mgr.save()

            log.info(f"[HPM] Active repository switched to: {active_repo}")
            return jsonify({
                "ok": True,
                "active_repository": active_repo
            })
        except Exception as e:
            log.error(f"[HPM] POST /api/hpm/settings/active_repository error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

