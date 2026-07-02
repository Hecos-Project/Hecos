"""
routes_packages_list.py
─────────────────────────────────────────────────────────────────────────────
Listing installed packages.
"""
from __future__ import annotations
import time
from flask import jsonify
from flask_login import login_required

from hecos.modules.web_ui.routes_packages_helpers import _get_hpm_components

# ── In-memory cache ───────────────────────────────────────────────────────────
_PKG_CACHE: dict = {}   # {"data": [...], "ts": float}
_PKG_CACHE_TTL = 30     # seconds — refreshed automatically on install/uninstall

def invalidate_packages_cache() -> None:
    """Clear the packages list cache. Call after install / uninstall / status change."""
    _PKG_CACHE.clear()
# ─────────────────────────────────────────────────────────────────────────────

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
                # Promote image fields to top-level BEFORE redacting snapshot
                p.setdefault("icon_url", raw_snap.get("icon_url"))
                p.setdefault("screenshots", raw_snap.get("screenshots") or [])
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
        Return the UNIFIED list of ALL modules visible in the Package Manager.
        Results are cached in-memory (TTL: _PKG_CACHE_TTL seconds).
        Cache is invalidated on install / uninstall / status change.
        """
        # ── Cache hit ─────────────────────────────────────────────────────────
        if _PKG_CACHE.get("data") and (time.time() - _PKG_CACHE.get("ts", 0)) < _PKG_CACHE_TTL:
            return jsonify({"ok": True, "packages": _PKG_CACHE["data"], "cached": True})
        # ──────────────────────────────────────────────────────────────────────

        try:
            import json as _json
            registry, _, _ = _get_hpm_components(_hecos_src)
            hpm_packages = registry.list_all()

            TYPE_TO_LEVEL = {
                "core_module": 1, "plugin": 2, "module": 2,
                "extension": 3, "app": 4, "widget": 5,
                "persona": 6, "theme": 7, "skill_pack": 8,
            }

            system_plugins = cfg_mgr.config.get("plugins", {})

            for p in hpm_packages:
                raw_snap = p.get("manifest_snapshot", {})
                if isinstance(raw_snap, str):
                    try: raw_snap = _json.loads(raw_snap)
                    except: raw_snap = {}

                pkg_tag = raw_snap.get("tag", "") or p.get("id", "").upper()

                p.setdefault("icon_url", raw_snap.get("icon_url"))
                p.setdefault("screenshots", raw_snap.get("screenshots") or [])

                if isinstance(p.get("manifest_snapshot"), (dict, str)):
                    p["manifest_snapshot"] = {
                        "id": raw_snap.get("id"),
                        "version": raw_snap.get("version"),
                        "config_panel": raw_snap.get("config_panel"),
                    }

                p_conf = system_plugins.get(pkg_tag, {})
                if "enabled" in p_conf:
                    p["status"] = "installed" if p_conf["enabled"] else "disabled"

                p["lazy_load"] = p_conf.get("lazy_load", False)
                p["level"] = TYPE_TO_LEVEL.get(p.get("type", "plugin"), 2)
                p["removable"] = True
                p.setdefault("fa_icon", "fa-cube")
                p.setdefault("cat", "Installed")

            # ── Save to cache ─────────────────────────────────────────────────
            _PKG_CACHE["data"] = hpm_packages
            _PKG_CACHE["ts"]   = time.time()
            # ──────────────────────────────────────────────────────────────────

            return jsonify({"ok": True, "packages": hpm_packages})

        except Exception as e:
            log.error(f"[HPM] GET /api/packages/all error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
