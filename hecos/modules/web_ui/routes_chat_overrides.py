import os
import yaml
from flask import request, jsonify
from hecos.core.logging import logger

def init_chat_overrides_routes(app, root_dir, logger):
    OVERRIDES_FILE = os.path.join(root_dir, "config", "data", "chat_overrides.yaml")

    @app.route("/hecos/api/chat/overrides", methods=["GET"])
    def get_chat_overrides():
        if not os.path.exists(OVERRIDES_FILE):
            return jsonify({"ok": True, "text": ""})
        try:
            with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return jsonify({"ok": True, "text": data.get("overrides", "")})
        except Exception as e:
            logger.error(f"[ChatOverrides] Error reading overrides: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/chat/overrides", methods=["POST"])
    def save_chat_overrides():
        try:
            data = request.json
            text = data.get("text", "")
            os.makedirs(os.path.dirname(OVERRIDES_FILE), exist_ok=True)
            with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
                yaml.dump({"overrides": text}, f, allow_unicode=True)
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[ChatOverrides] Error saving overrides: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
