"""
routes_packages.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Package Manager REST API

Endpoints:
  GET  /api/packages                  List all installed packages
  POST /api/packages/install          Upload and install a .hpkg file
  GET  /api/packages/<id>             Get details of a specific package
  GET  /api/packages/<id>/manifest    Get the stored manifest snapshot
  PATCH /api/packages/<id>/status     Enable or disable a package
  DELETE /api/packages/<id>           Uninstall a package

All routes require login.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import os
import threading
from flask import jsonify, request
from flask_login import login_required

from hecos.core.logging import logger
from hecos.core.i18n import t


def _get_hpm_components(hecos_root: str):
    """
    Lazily initialize HPM components. Keeps them as module-level singletons
    so the registry connection is reused across requests.
    """
    import sys
    if not hasattr(sys, "_hecos_hpm_registry"):
        from hecos.core.package_manager.registry import PackageRegistry
        from hecos.core.package_manager.installer import PackageInstaller
        from hecos.core.package_manager.uninstaller import PackageUninstaller
        from hecos.core.system.version import VERSION

        data_dir = os.path.join(hecos_root, "data")
        os.makedirs(data_dir, exist_ok=True)

        registry = PackageRegistry(data_dir=data_dir)
        installer = PackageInstaller(
            hecos_root=hecos_root,
            registry=registry,
            hecos_version=VERSION,
            event_callback=_hpm_event_broadcast,
        )
        uninstaller = PackageUninstaller(
            hecos_root=hecos_root,
            registry=registry,
            event_callback=_hpm_event_broadcast,
        )

        sys._hecos_hpm_registry = registry
        sys._hecos_hpm_installer = installer
        sys._hecos_hpm_uninstaller = uninstaller

    return (
        sys._hecos_hpm_registry,
        sys._hecos_hpm_installer,
        sys._hecos_hpm_uninstaller,
    )


def _hpm_event_broadcast(event_name: str, payload: dict) -> None:
    """Broadcast HPM events to connected WebUI clients via SSE."""
    try:
        import sys
        sm = getattr(sys, "hecos_state_manager", None)
        if sm and hasattr(sm, "add_event"):
            sm.add_event(event_name, payload)
            logger.debug(f"[HPM:Routes] Event broadcast: {event_name} → {payload.get('id')}")
    except Exception as e:
        logger.debug(f"[HPM:Routes] Could not broadcast event: {e}")


def init_package_routes(app, hecos_root: str, cfg_mgr, _log=None):
    """Register all HPM REST routes on the Flask app."""

    log = _log or logger

    # Resolve the actual hecos/ source directory (not the project root)
    _hecos_src = os.path.join(hecos_root, "hecos")
    if not os.path.isdir(_hecos_src):
        _hecos_src = hecos_root  # fallback: already pointing at hecos/

    # ── GET /api/packages ─────────────────────────────────────────────────────
    @app.route("/api/packages", methods=["GET"])
    @login_required
    def api_list_packages():
        """Return all installed packages."""
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            packages = registry.list_all()
            # Redact large manifest_snapshot from listing to keep response small
            for p in packages:
                if isinstance(p.get("manifest_snapshot"), dict):
                    snap = p["manifest_snapshot"]
                    p["manifest_snapshot"] = {
                        "id": snap.get("id"),
                        "version": snap.get("version"),
                        "config_panel": snap.get("config_panel"),
                    }
            return jsonify({"ok": True, "packages": packages})
        except Exception as e:
            log.error(f"[HPM] GET /api/packages error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET /api/packages/all ─────────────────────────────────────────────────
    @app.route("/api/packages/all", methods=["GET"])
    @login_required
    def api_list_all_packages():
        """
        Return the UNIFIED list of ALL modules visible in the Package Manager:
          - Level 1 (Core):  built-in modules, not removable
          - Level 2+ (HPM):  packages installed via HPM from packages.db
        """
        try:
            registry, _, _ = _get_hpm_components(_hecos_src)
            hpm_packages = registry.list_all()

            # Redact large snapshots
            for p in hpm_packages:
                if isinstance(p.get("manifest_snapshot"), dict):
                    snap = p["manifest_snapshot"]
                    p["manifest_snapshot"] = {
                        "id": snap.get("id"),
                        "version": snap.get("version"),
                        "config_panel": snap.get("config_panel"),
                    }

            # ── HPM packages get their level from type
            TYPE_TO_LEVEL = {
                "core_module": 1, "plugin": 2, "module": 2,
                "extension": 3, "app": 4, "widget": 5,
                "persona": 6, "theme": 7, "skill_pack": 8,
            }
            
            system_plugins = cfg_mgr.config.get("plugins", {})
            
            for p in hpm_packages:
                tag = p.get("id", "")
                p_conf = system_plugins.get(tag, {})
                
                # system.yaml overrides HPM status for true runtime state
                if "enabled" in p_conf:
                    p["status"] = "installed" if p_conf["enabled"] else "disabled"
                    
                p["lazy_load"] = p_conf.get("lazy_load", False)
                p["level"] = TYPE_TO_LEVEL.get(p.get("type", "plugin"), 2)
                p["removable"] = True
                p.setdefault("fa_icon", "fa-cube")
                p.setdefault("cat", "Installed")

            return jsonify({"ok": True, "packages": hpm_packages})

        except Exception as e:
            log.error(f"[HPM] GET /api/packages/all error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/packages/install ────────────────────────────────────────────
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
                response = {
                    "ok": True,
                    "id": result.package_id,
                    "warnings": result.warnings,
                }
                if result.dep_report and result.dep_report.has_issues:
                    response["dep_issues"] = result.dep_report.summary
                return jsonify(response)
            else:
                return jsonify({
                    "ok": False,
                    "error": result.error,
                    "warnings": result.warnings,
                }), 422

        except Exception as e:
            log.error(f"[HPM] Install error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET /api/packages/<id> ────────────────────────────────────────────────
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

    # ── GET /api/packages/<id>/manifest ───────────────────────────────────────
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

    # ── PATCH /api/packages/<id>/status ───────────────────────────────────────
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
            if not registry.is_installed(pkg_id):
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not found"}), 404
            ok = registry.set_status(pkg_id, status)
            if ok:
                _hpm_event_broadcast("hpm:package_status_changed", {
                    "id": pkg_id, "status": status
                })
            return jsonify({"ok": ok, "id": pkg_id, "status": status})
        except Exception as e:
            log.error(f"[HPM] PATCH /api/packages/{pkg_id}/status error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── DELETE /api/packages/<id> ─────────────────────────────────────────────
    @app.route("/api/packages/<pkg_id>", methods=["DELETE"])
    @login_required
    def api_uninstall_package(pkg_id):
        """Uninstall a package by its id."""
        try:
            registry, _, uninstaller = _get_hpm_components(_hecos_src)
            if not registry.is_installed(pkg_id):
                return jsonify({"ok": False, "error": f"Package '{pkg_id}' not installed"}), 404

            result = uninstaller.uninstall(pkg_id)

            if result.success:
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

    # ── GET /api/packages/remote/search ─────────────────────────────────────
    @app.route("/api/packages/remote/search", methods=["GET"])
    @login_required
    def api_remote_search():
        """
        STUB: Search the remote package registry.
        Returns empty results until the remote registry is implemented.
        """
        from hecos.core.package_manager.remote_registry import RemoteRegistryClient
        client = RemoteRegistryClient()
        query = request.args.get("q", "")
        results = client.search(query=query)
        return jsonify({
            "ok": True,
            "results": results,
            "remote_available": client.is_available,
        })

    log.info("[HPM] Package Manager routes registered.")
