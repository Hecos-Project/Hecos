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

            # ── Core modules (L1) ─────────────────────────────────────────────
            # Mirrors config_manifest.js CONFIG_HUB.modules where isCore=true,
            # plus the non-core plugins that are shipped built-in with Hecos.
            # All built-in modules are shipped with Hecos — not removable
            BUILTIN_MODULES = [
                # Level 1 — Core (isCore: true in config_manifest.js)
                {"id": "backend",    "name": "AI Backend",      "fa_icon": "fa-server",          "type": "core_module", "level": 1, "tag": "MODELS",       "cat": "Intelligenza", "description": t("hpm_desc_backend")},
                {"id": "keymanager", "name": "Key Manager",     "fa_icon": "fa-key",             "type": "core_module", "level": 1, "tag": "KEYMANAGER",   "cat": "Intelligenza", "description": t("hpm_desc_keymanager")},
                {"id": "routing",    "name": "AI Routing",      "fa_icon": "fa-route",           "type": "core_module", "level": 1, "tag": "ROUTING",      "cat": "Intelligenza", "description": t("hpm_desc_routing")},
                {"id": "ia",         "name": "Personality",     "fa_icon": "fa-user-astronaut",  "type": "core_module", "level": 1, "tag": "PERSONA",      "cat": "Intelligenza", "description": t("hpm_desc_ia")},
                {"id": "filters",    "name": "Filters",         "fa_icon": "fa-filter",          "type": "core_module", "level": 1, "tag": "FILTERS",      "cat": "Intelligenza", "description": t("hpm_desc_filters")},
                {"id": "memory",     "name": "Memory",          "fa_icon": "fa-memory",          "type": "core_module", "level": 1, "tag": "MEMORY",       "cat": "Intelligenza", "description": t("hpm_desc_memory")},
                {"id": "agent",      "name": "AI Agent",        "fa_icon": "fa-robot",           "type": "core_module", "level": 1, "tag": "AGENT",        "cat": "Intelligenza", "description": t("hpm_desc_agent")},
                {"id": "aesthetics", "name": "Aesthetics",      "fa_icon": "fa-palette",         "type": "core_module", "level": 1, "tag": "AESTHETICS",   "cat": "Multimedia", "description": t("hpm_desc_aesthetics")},
                {"id": "mcp",        "name": "MCP Bridge",      "fa_icon": "fa-plug",            "type": "core_module", "level": 1, "tag": "MCP_BRIDGE",   "cat": "Connettività", "description": t("hpm_desc_mcp")},
                {"id": "bridge",     "name": "Bridge",          "fa_icon": "fa-project-diagram", "type": "core_module", "level": 1, "tag": "BRIDGE",       "cat": "Connettività", "description": t("hpm_desc_bridge")},
                {"id": "templates",  "name": "Templates",       "fa_icon": "fa-file-alt",        "type": "core_module", "level": 1, "tag": "TEMPLATES",    "cat": "Connettività", "description": t("hpm_desc_templates")},
                {"id": "flows",      "name": "Flows Engine",    "fa_icon": "fa-project-diagram", "type": "core_module", "level": 1, "tag": "FLOWS",        "cat": "Risorse", "description": t("hpm_desc_flows")},
                {"id": "sysnet",     "name": "Sys & Net",       "fa_icon": "fa-globe",           "type": "core_module", "level": 1, "tag": "SYS_NET",      "cat": "Sistema", "description": t("hpm_desc_sysnet")},
                {"id": "automation", "name": "OS Automation",   "fa_icon": "fa-magic",           "type": "core_module", "level": 1, "tag": "AUTOMATION",   "cat": "Sistema", "description": t("hpm_desc_automation")},
                {"id": "browser",    "name": "AI Browser",      "fa_icon": "fa-window-maximize", "type": "core_module", "level": 1, "tag": "BROWSER",      "cat": "Sistema", "description": t("hpm_desc_browser")},
                {"id": "executor",   "name": "Executor",        "fa_icon": "fa-bolt",            "type": "core_module", "level": 1, "tag": "EXECUTOR",     "cat": "Sistema", "description": t("hpm_desc_executor")},
                {"id": "hdcs",       "name": "HDCS Commands",   "fa_icon": "fa-terminal",        "type": "core_module", "level": 1, "tag": "HDCS",         "cat": "Sistema", "description": t("hpm_desc_hdcs")},
                {"id": "widgets",    "name": "Widgets Engine",  "fa_icon": "fa-cubes",           "type": "core_module", "level": 1, "tag": "WIDGETS",      "cat": "Sistema", "description": t("hpm_desc_widgets")},
                {"id": "webui",      "name": "Web Interface",   "fa_icon": "fa-desktop",         "type": "core_module", "level": 1, "tag": "WEB_UI",       "cat": "Sistema", "description": t("hpm_desc_webui")},
                {"id": "backup",     "name": "Backup",          "fa_icon": "fa-shield-halved",   "type": "core_module", "level": 1, "tag": "BACKUP",       "cat": "Sistema", "description": t("hpm_desc_backup")},
                {"id": "users",      "name": "Users",           "fa_icon": "fa-users-cog",       "type": "core_module", "level": 1, "tag": "USERS",        "cat": "Sistema", "description": t("hpm_desc_users")},
                # Level 2 — Built-in Plugins (shipped with Hecos, not installed via HPM)
                {"id": "voice",      "name": "Voice System",    "fa_icon": "fa-microphone-alt",  "type": "plugin",      "level": 2, "tag": "VOICE",        "cat": "Multimedia", "description": t("hpm_desc_voice")},
                {"id": "media",      "name": "Media Player",    "fa_icon": "fa-music",           "type": "app",         "level": 4, "tag": "MEDIA_PLAYER", "cat": "Multimedia", "description": t("hpm_desc_media")},
                {"id": "igen",       "name": "Image Gen",       "fa_icon": "fa-image",           "type": "app",         "level": 4, "tag": "IMAGE_GEN",    "cat": "Multimedia", "description": t("hpm_desc_igen")},
                {"id": "messenger",  "name": "Messenger",       "fa_icon": "fa-comment-alt",     "type": "plugin",      "level": 2, "tag": "MESSENGER",    "cat": "Connettività", "description": t("hpm_desc_messenger")},
                {"id": "contacts",   "name": "Contacts",        "fa_icon": "fa-address-book",    "type": "plugin",      "level": 2, "tag": "CONTACTS",     "cat": "Connettività", "description": t("hpm_desc_contacts")},
                {"id": "mail",       "name": "Mail",            "fa_icon": "fa-envelope",        "type": "app",         "level": 4, "tag": "MAIL",         "cat": "Connettività", "description": t("hpm_desc_mail")},
                {"id": "remote-triggers", "name": "Remote Triggers", "fa_icon": "fa-mobile-alt", "type": "plugin",     "level": 2, "tag": "REMOTE_TRIGGERS", "cat": "Connettività", "description": t("hpm_desc_remote_triggers")},
                {"id": "drive",      "name": "Hecos Drive",     "fa_icon": "fa-hdd",             "type": "app",         "level": 4, "tag": "DRIVE",        "cat": "Risorse", "description": t("hpm_desc_drive")},
                {"id": "web",        "name": "Web Search",      "fa_icon": "fa-globe",           "type": "plugin",      "level": 2, "tag": "WEB",          "cat": "Sistema", "description": t("hpm_desc_web")},
                {"id": "webcam",     "name": "Webcam",          "fa_icon": "fa-camera",          "type": "plugin",      "level": 2, "tag": "WEBCAM",       "cat": "Sistema", "description": t("hpm_desc_webcam")},
                {"id": "reminder",   "name": "Reminder",        "fa_icon": "fa-clock",           "type": "app",         "level": 4, "tag": "REMINDER",     "cat": "Sistema", "description": t("hpm_desc_reminder")},
                {"id": "calendar",   "name": "Calendar",        "fa_icon": "fa-calendar-alt",    "type": "app",         "level": 4, "tag": "CALENDAR",     "cat": "Sistema", "description": t("hpm_desc_calendar")},
                {"id": "lists",      "name": "Lists",           "fa_icon": "fa-list-check",      "type": "plugin",      "level": 2, "tag": "LISTS",        "cat": "Sistema", "description": t("hpm_desc_lists")},
                {"id": "weather",    "name": "Weather",         "fa_icon": "fa-cloud-sun",       "type": "plugin",      "level": 2, "tag": "WEATHER",      "cat": "Sistema", "description": t("hpm_desc_weather")},
                {"id": "map",        "name": "Maps",            "fa_icon": "fa-map-marked-alt",  "type": "plugin",      "level": 2, "tag": "MAP",          "cat": "Sistema", "description": t("hpm_desc_map")},
                # Level 3 — Extensions (children of plugins)
                {"id": "drive-editor", "name": "Drive Editor",  "fa_icon": "fa-edit",            "type": "extension",   "level": 3, "tag": "DRIVE_EDITOR", "cat": "Risorse", "parent_tag": "DRIVE", "description": t("hpm_desc_drive_editor")},
            ]


            system_plugins = cfg_mgr.config.get("plugins", {})

            for m in BUILTIN_MODULES:
                tag = m.get("id", "")
                p_conf = system_plugins.get(tag, {})
                m.setdefault("removable", False)
                m["status"] = "installed" if p_conf.get("enabled", True) else "disabled"
                m["lazy_load"] = p_conf.get("lazy_load", False)
                m.setdefault("version", "built-in")
                m.setdefault("author", "Hecos Core")
                # Description is already set for core modules, fallback just in case:
                m.setdefault("description", t("hpm_desc_fallback"))
                m.setdefault("installed_at", None)

            # HPM packages get their level from type
            TYPE_TO_LEVEL = {
                "core_module": 1, "plugin": 2, "module": 2,
                "extension": 3, "app": 4, "widget": 5,
                "persona": 6, "theme": 7, "skill_pack": 8,
            }
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

            unified = BUILTIN_MODULES + hpm_packages
            return jsonify({"ok": True, "packages": unified})

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
