"""
routes_config_vision.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Vision (Multimodal Perception) Configuration Routes
Isolated CRUD for vision.yaml via VisionConfig schema.
─────────────────────────────────────────────────────────────────────────────
"""
import os
from flask import request, jsonify


def init_config_vision_routes(app, root_dir, logger):
    """Register vision.yaml CRUD routes."""

    _vision_path = os.path.join(root_dir, "hecos", "config", "data", "vision.yaml")

    @app.route("/hecos/config/vision", methods=["GET"])
    def get_vision_config():
        try:
            from hecos.config import load_yaml
            from hecos.config.schemas.vision_schema import VisionConfig
            if not os.path.exists(_vision_path):
                # Return default schema if file not yet present
                default_model = VisionConfig()
                return jsonify(default_model.model_dump())
            model = load_yaml(_vision_path, VisionConfig)
            return jsonify(model.model_dump())
        except Exception as e:
            logger.error(f"[WebUI] GET /hecos/config/vision error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/hecos/config/vision", methods=["POST"])
    def post_vision_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400

            from hecos.config import save_yaml
            from hecos.config.schemas.vision_schema import VisionConfig
            model = VisionConfig(**incoming)
            if save_yaml(_vision_path, model):
                logger.info("[WebUI] Vision configuration saved successfully.")
                # Also notify runtime cache if loaded
                try:
                    from hecos.modules.web_ui.vision.config import reload_vision_config
                    reload_vision_config()
                except Exception:
                    pass
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/config/vision error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

