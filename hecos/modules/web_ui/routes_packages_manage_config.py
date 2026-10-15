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

    def _get_hpm_auth_file():
        return os.path.join(_hecos_src, "data", "hpm_auth.json")

    def _get_hpm_token():
        auth_file = _get_hpm_auth_file()
        if os.path.isfile(auth_file):
            try:
                import json
                with open(auth_file, "r", encoding="utf-8") as f:
                    tok = json.load(f).get("github_token", "").strip()
                    if tok:
                        return tok
            except Exception:
                pass
        env_tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if env_tok and env_tok.strip():
            return env_tok.strip()
        return ""

    def _save_hpm_token(token: str):
        auth_file = _get_hpm_auth_file()
        os.makedirs(os.path.dirname(auth_file), exist_ok=True)
        import json
        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump({"github_token": token.strip()}, f, indent=2)

    def _auto_repo_name(url: str, index: int = 1) -> str:
        url_clean = (url or "").strip().rstrip("/")
        if "hecos-project.github.io" in url_clean or "Hecos-Packages" in url_clean:
            return "Hecos Official"
        import re
        gh = re.search(r"github\.com/[^/]+/([^/#?]+)", url_clean, re.IGNORECASE) or \
             re.search(r"raw\.githubusercontent\.com/[^/]+/([^/#?]+)", url_clean, re.IGNORECASE)
        if gh:
            repo_name = gh.group(1)
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            return repo_name
        if "\\" in url_clean or "/" in url_clean:
            base = os.path.basename(url_clean.replace("\\", "/"))
            if base and not base.endswith(".json"):
                return base
            parent = os.path.basename(os.path.dirname(url_clean.replace("\\", "/")))
            if parent and parent not in ("store", "packages", ""):
                return parent
        return f"Repository {index}"

    def _normalize_repo_entry(entry, index: int = 1) -> dict | None:
        if isinstance(entry, dict):
            url = str(entry.get("url") or "").strip()
            name = str(entry.get("name") or "").strip()
        elif hasattr(entry, "url"):
            url = str(getattr(entry, "url", "") or "").strip()
            name = str(getattr(entry, "name", "") or "").strip()
        elif isinstance(entry, str):
            raw = entry.strip()
            if "|" in raw:
                parts = [p.strip() for p in raw.split("|", 1)]
                if parts[0].startswith(("http://", "https://", "file://")) or ":\\" in parts[0] or parts[0].startswith("/"):
                    url = parts[0]
                    name = parts[1]
                else:
                    name = parts[0]
                    url = parts[1]
            else:
                url = raw
                name = ""
        else:
            return None

        if not url:
            return None
        if not name:
            name = _auto_repo_name(url, index)
        return {"name": name, "url": url}

    @app.route("/api/hpm/settings/repositories", methods=["GET"])
    @login_required
    def api_hpm_get_repositories():
        """Returns the list of configured package repositories and the active one."""
        default_repo_url = "https://hecos-project.github.io/store/index.json"
        raw_repos = []
        active = default_repo_url
        github_token = _get_hpm_token()
        try:
            if cfg_mgr:
                hpm_cfg = cfg_mgr.get("hpm") or {}
                if isinstance(hpm_cfg, dict):
                    raw_repos = list(hpm_cfg.get("repositories") or [])
                    active = hpm_cfg.get("store_catalog_url") or default_repo_url
                elif hasattr(hpm_cfg, "repositories"):
                    raw_repos = list(getattr(hpm_cfg, "repositories", []) or [])
                    active = getattr(hpm_cfg, "store_catalog_url", default_repo_url) or default_repo_url

            normalized = []
            seen_urls = set()
            for idx, r in enumerate(raw_repos, 1):
                item = _normalize_repo_entry(r, idx)
                if item and item["url"] not in seen_urls:
                    normalized.append(item)
                    seen_urls.add(item["url"])

            if not normalized:
                normalized = [{"name": "Hecos Official", "url": default_repo_url}]
                seen_urls.add(default_repo_url)

            if default_repo_url not in seen_urls:
                normalized.insert(0, {"name": "Hecos Official", "url": default_repo_url})
                seen_urls.add(default_repo_url)

            valid_urls = [r["url"] for r in normalized]
            if not active or active not in valid_urls:
                active = valid_urls[0]

            return jsonify({
                "ok": True,
                "repositories": normalized,
                "active_repository": active,
                "github_token": github_token
            })
        except Exception as e:
            log.error(f"[HPM] GET /api/hpm/settings/repositories error: {e}")
            fallback = [{"name": "Hecos Official", "url": default_repo_url}]
            return jsonify({"ok": False, "error": str(e), "repositories": fallback, "active_repository": default_repo_url, "github_token": ""}), 500

    @app.route("/api/hpm/settings/repositories", methods=["POST"])
    @login_required
    def api_hpm_set_repositories():
        """Updates the list of configured repositories and optionally the active repository."""
        default_repo_url = "https://hecos-project.github.io/store/index.json"
        try:
            data = request.get_json(silent=True) or {}
            raw_repos = data.get("repositories", [])
            active_repo = (data.get("active_repository") or "").strip()
            github_token = data.get("github_token")

            if isinstance(raw_repos, str):
                lines = [l.strip() for l in raw_repos.replace(",", "\n").splitlines()]
            elif isinstance(raw_repos, list):
                lines = raw_repos
            else:
                lines = []

            cleaned = []
            seen_urls = set()
            for idx, l in enumerate(lines, 1):
                if isinstance(l, str) and l.strip().startswith("#"):
                    continue
                item = _normalize_repo_entry(l, idx)
                if item and item["url"] not in seen_urls:
                    cleaned.append(item)
                    seen_urls.add(item["url"])

            if not cleaned:
                cleaned = [{"name": "Hecos Official", "url": default_repo_url}]
                seen_urls.add(default_repo_url)

            valid_urls = [r["url"] for r in cleaned]
            if not active_repo or active_repo not in valid_urls:
                active_repo = valid_urls[0]

            # Store the token safely in local untracked hpm_auth.json
            if github_token is not None:
                _save_hpm_token(github_token)

            if cfg_mgr:
                if "hpm" not in cfg_mgr.config or not isinstance(cfg_mgr.config["hpm"], dict):
                    cfg_mgr.config["hpm"] = {}
                cfg_mgr.config["hpm"]["repositories"] = cleaned
                cfg_mgr.config["hpm"]["store_catalog_url"] = active_repo
                # CRITICAL SECURITY: Never write private tokens into system.yaml (which is tracked by git)
                cfg_mgr.config["hpm"].pop("github_token", None)
                cfg_mgr.save()

            saved_token = _get_hpm_token()
            log.info(f"[HPM] Repositories updated ({len(cleaned)} repos, active: {active_repo})")
            return jsonify({
                "ok": True,
                "repositories": cleaned,
                "active_repository": active_repo,
                "github_token": saved_token
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

                # Properly extract known URLs from dicts, models, or strings
                known_urls = [
                    (r.get("url") if isinstance(r, dict) else (getattr(r, "url", str(r)))).strip()
                    for r in repos
                    if r
                ]
                if active_repo not in known_urls:
                    repos.append({"name": _auto_repo_name(active_repo, len(repos) + 1), "url": active_repo})
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

