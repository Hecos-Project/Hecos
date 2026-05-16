"""
routes_config_agent.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Agent Configuration Routes
Isolated CRUD for agent.yaml via AgentConfig schema.
Keeping this separate from the main system.yaml save path prevents
partial payloads from corrupting agent settings.
─────────────────────────────────────────────────────────────────────────────
"""
import os
from flask import request, jsonify


def init_config_agent_routes(app, root_dir, logger):
    """Register agent.yaml CRUD routes."""

    _agent_path = os.path.join(root_dir, "hecos", "config", "data", "agent.yaml")

    @app.route("/hecos/config/agent", methods=["GET"])
    def get_agent_config():
        try:
            from hecos.config import load_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            model = load_yaml(_agent_path, AgentConfig)
            return jsonify(model.model_dump())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/hecos/config/agent", methods=["POST"])
    def post_agent_config():
        try:
            incoming = request.get_json(force=True)
            if not isinstance(incoming, dict):
                return jsonify({"ok": False, "error": "Invalid payload"}), 400

            from hecos.config import save_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            model = AgentConfig(**incoming)
            if save_yaml(_agent_path, model):
                logger.info("[WebUI] Agent configuration saved successfully.")
                return jsonify({"ok": True})
            return jsonify({"ok": False, "error": "Save failed"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/config/agent error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500
