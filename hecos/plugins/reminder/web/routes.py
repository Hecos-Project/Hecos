"""
Autonomous API routes for the Reminder package.
Handles config persistence and ringtone listing.
Mapped via 'api_routes_file' in hpkg_manifest.toml.
"""


def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os
    import sys
    from flask import request, jsonify
    from flask_login import login_required

    # Ensure the plugin directory is importable
    plugin_path = os.path.dirname(os.path.abspath(__file__))  # web/
    pkg_root    = os.path.dirname(plugin_path)               # reminder/
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)

    from reminder_config.config_manager import get_reminder_config, save_reminder_section

    # ── 1. Config GET ─────────────────────────────────────────────────────────

    @app.route("/hecos/api/plugins/reminder/config", methods=["GET"])
    @login_required
    def get_reminder_config_api():
        try:
            return jsonify({"ok": True, "reminder": get_reminder_config()})
        except Exception as exc:
            logger.error(f"[Reminder] GET config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── 2. Config POST ────────────────────────────────────────────────────────

    @app.route("/hecos/api/plugins/reminder/config", methods=["POST"])
    @login_required
    def post_reminder_config_api():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400

            section = incoming.get("reminder", incoming)   # accept both wrapped and flat
            if save_reminder_section(section):
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500

        except Exception as exc:
            logger.error(f"[Reminder] POST config error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── 3. Ringtone listing ───────────────────────────────────────────────────

    @app.route("/api/ext/reminder/ringtones", methods=["GET"])
    def list_reminder_ringtones():
        """Return available ringtone files from the plugin's assets/sounds folder."""
        try:
            sounds_dir = os.path.join(root_dir, "assets", "sounds")
            if not os.path.isdir(sounds_dir):
                return jsonify({"ok": True, "ringtones": []})
            files = sorted([
                f for f in os.listdir(sounds_dir)
                if f.lower().endswith((".mp3", ".wav", ".ogg"))
            ])
            return jsonify({"ok": True, "ringtones": files})
        except Exception as exc:
            logger.error(f"[Reminder] ringtones error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
