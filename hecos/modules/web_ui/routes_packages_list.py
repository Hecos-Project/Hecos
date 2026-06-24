"""
routes_packages_list.py
─────────────────────────────────────────────────────────────────────────────
Listing installed packages.
"""
from __future__ import annotations
from flask import jsonify
from flask_login import login_required

from hecos.modules.web_ui.routes_packages_helpers import _get_hpm_components

def register_list_routes(app, _hecos_src: str, cfg_mgr, log):
    
    @app.route("/api/packages", methods=["GET"])
    @login_required
    def api_list_packages():
        """Return all installed packages."""
        try:
            import json as _json
            registry, _, _ = _get_hpm_components(_hecos_src)
            packages = registry.list_all()
            # Redact large manifest_snapshot from listing to keep response small
            for p in packages:
                raw_snap = p.get("manifest_snapshot", {})
                if isinstance(raw_snap, str):
                    try: raw_snap = _json.loads(raw_snap)
                    except: raw_snap = {}
                if isinstance(p.get("manifest_snapshot"), dict) or isinstance(p.get("manifest_snapshot"), str):
                    p["manifest_snapshot"] = {
                        "id": raw_snap.get("id"),
                        "version": raw_snap.get("version"),
                        "config_panel": raw_snap.get("config_panel"),
                    }
            return jsonify({"ok": True, "packages": packages})
        except Exception as e:
            log.error(f"[HPM] GET /api/packages error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/packages/all", methods=["GET"])
    @login_required
    def api_list_all_packages():
        """
        Return the UNIFIED list of ALL modules visible in the Package Manager:
          - Level 1 (Core):  built-in modules, not removable
          - Level 2+ (HPM):  packages installed via HPM from packages.db
        """
        try:
            import json as _json
            registry, _, _ = _get_hpm_components(_hecos_src)
            hpm_packages = registry.list_all()

            # ── HPM packages get their level from type
            TYPE_TO_LEVEL = {
                "core_module": 1, "plugin": 2, "module": 2,
                "extension": 3, "app": 4, "widget": 5,
                "persona": 6, "theme": 7, "skill_pack": 8,
            }
            
            system_plugins = cfg_mgr.config.get("plugins", {})
            
            for p in hpm_packages:
                # ── Extract tag from FULL snapshot BEFORE redacting ──
                raw_snap = p.get("manifest_snapshot", {})
                if isinstance(raw_snap, str):
                    try: raw_snap = _json.loads(raw_snap)
                    except: raw_snap = {}
                
                # Store tag using the manifest tag field (e.g. "WEBCAM_WIDGET")
                pkg_tag = raw_snap.get("tag", "") or p.get("id", "").upper()

                # Redact the large snapshot now that we've extracted what we need
                if isinstance(p.get("manifest_snapshot"), (dict, str)):
                    p["manifest_snapshot"] = {
                        "id": raw_snap.get("id"),
                        "version": raw_snap.get("version"),
                        "config_panel": raw_snap.get("config_panel"),
                    }

                p_conf = system_plugins.get(pkg_tag, {})
                
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
