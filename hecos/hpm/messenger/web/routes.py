"""
MODULE: Messenger — API Routes
PACKAGE: messenger
"""

from flask import request, jsonify

def init_plugin_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    import os
    import sys

    plugin_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if plugin_path not in sys.path:
        sys.path.insert(0, plugin_path)

    @app.route("/hecos/api/plugins/messenger/config", methods=["GET"])
    def hpm_messenger_get_config():
        try:
            from messenger_config.config_manager import get_config
            cfg = get_config()
            return jsonify({"ok": True, "config": cfg})
        except Exception as e:
            logger.error(f"[Messenger] GET config error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/plugins/messenger/config", methods=["POST"])
    def hpm_messenger_post_config():
        try:
            data = request.get_json(force=True) or {}
            from messenger_config.config_manager import get_config, save_config
            cfg = get_config()

            if "telegram" in data:
                cfg.setdefault("telegram", {}).update(data["telegram"])
            if "whatsapp" in data:
                cfg.setdefault("whatsapp", {}).update(data["whatsapp"])
            if "discord" in data:
                cfg.setdefault("discord", {}).update(data["discord"])

            save_config(cfg)
            
            try:
                import importlib
                plugin_main = importlib.import_module("hpm.messenger.main")
                plugin_main.on_load()
                logger.info(f"[Messenger] Config saved and hot-reloaded.")
            except Exception as e:
                logger.error(f"[Messenger] Error hot-reloading config: {e}")

            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[Messenger] POST config error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
