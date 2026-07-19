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
def register_manage_info_routes(app, _hecos_src: str, cfg_mgr, log):
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

