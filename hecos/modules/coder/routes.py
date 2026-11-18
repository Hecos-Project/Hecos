"""
Hecos Coder — HPM Standalone API Routes
Mapped via 'api_routes_file' in hpkg_manifest.toml.
"""

from __future__ import annotations

from flask import jsonify, request


def init_plugin_routes(app, cfg_mgr, hecos_root, logger):
    """Register Coder configuration API routes on the Flask app."""

    @app.route("/hecos/api/plugins/coder/config", methods=["GET"])
    def get_coder_config():
        try:
            exec_cfg = (cfg_mgr.config.get("plugins") or {}).get("EXECUTOR", {}) if cfg_mgr else {}
            coder_cfg = (cfg_mgr.config.get("plugins") or {}).get("CODER", {}) if cfg_mgr else {}
            merged = dict(exec_cfg)
            merged.update(coder_cfg)
            return jsonify({"ok": True, "config": merged})
        except Exception as exc:
            logger.error(f"[Coder] GET config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/hecos/api/plugins/coder/config", methods=["POST"])
    def save_coder_config():
        try:
            data = request.get_json(force=True) or {}
            if cfg_mgr:
                plugins = cfg_mgr.config.setdefault("plugins", {})
                ex = plugins.setdefault("EXECUTOR", {})
                cd = plugins.setdefault("CODER", {})
                for k, v in data.items():
                    ex[k] = v
                    cd[k] = v
                cfg_mgr.save()
            return jsonify({"ok": True})
        except Exception as exc:
            logger.error(f"[Coder] POST config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
