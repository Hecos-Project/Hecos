"""
routes_config_routing.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — LLM Routing Override Configuration Routes
Isolated CRUD for routing_overrides.yaml via RoutingOverrides schema.
─────────────────────────────────────────────────────────────────────────────
"""
import os
from flask import request, jsonify


def init_config_routing_routes(app, root_dir, logger):
    """Register routing overrides CRUD routes."""

    _routing_path = os.path.join(root_dir, "hecos", "config", "data", "routing_overrides.yaml")

    @app.route("/hecos/config/routing", methods=["GET"])
    def get_routing_config():
        try:
            from hecos.config import load_yaml
            from hecos.config.schemas.routing_schema import RoutingOverrides
            model = load_yaml(_routing_path, RoutingOverrides)
            return jsonify(model.overrides)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/hecos/config/routing", methods=["POST"])
    def post_routing_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400

            from hecos.config import save_yaml
            from hecos.config.schemas.routing_schema import RoutingOverrides
            model = RoutingOverrides(overrides=incoming)
            if save_yaml(_routing_path, model):
                logger.info("[WebUI] Routing overrides saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/config/routing error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
