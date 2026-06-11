"""
routes_config_routing.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — LLM Routing Override Configuration Routes
Isolated CRUD for routing_overrides.yaml via RoutingOverrides schema.
─────────────────────────────────────────────────────────────────────────────
"""
import os
import json
import shutil
from flask import request, jsonify

_REGISTRY_PATH_REL = os.path.join("hecos", "core", "registry.json")


def init_config_routing_routes(app, root_dir, logger):
    """Register routing overrides CRUD routes."""

    _routing_path = os.path.join(root_dir, "hecos", "config", "data", "routing_overrides.yaml")
    _backup_path  = os.path.join(root_dir, "hecos", "config", "data", "routing_overrides.backup.yaml")
    _registry_path = os.path.join(root_dir, _REGISTRY_PATH_REL)

    # ── GET current user overrides ────────────────────────────────────────────
    @app.route("/hecos/config/routing", methods=["GET"])
    def get_routing_config():
        try:
            from hecos.config import load_yaml
            from hecos.config.schemas.routing_schema import RoutingOverrides
            model = load_yaml(_routing_path, RoutingOverrides)
            return jsonify(model.overrides)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ── POST save user overrides ──────────────────────────────────────────────
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

    # ── GET default routing_instructions from registry.json ──────────────────
    @app.route("/hecos/config/routing/defaults", methods=["GET"])
    def get_routing_defaults():
        """Return all default routing_instructions from registry.json."""
        try:
            if not os.path.exists(_registry_path):
                return jsonify({"error": "registry.json not found"}), 404
            with open(_registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            defaults = {
                tag: info.get("routing_instructions", "")
                for tag, info in registry.items()
            }
            return jsonify(defaults)
        except Exception as exc:
            logger.error(f"[WebUI] GET /hecos/config/routing/defaults error: {exc}")
            return jsonify({"error": str(exc)}), 500

    # ── POST reset overrides to defaults (with auto-backup) ──────────────────
    @app.route("/hecos/config/routing/reset", methods=["POST"])
    def reset_routing_to_defaults():
        """Backup the current YAML and reset overrides to registry defaults."""
        try:
            # 1. Auto-backup current file
            if os.path.exists(_routing_path):
                shutil.copy2(_routing_path, _backup_path)
                logger.info(f"[WebUI] Routing overrides backed up to {_backup_path}")

            # 2. Build defaults from registry
            if not os.path.exists(_registry_path):
                return jsonify({"ok": False, "error": "registry.json not found"}), 404
            with open(_registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            defaults = {
                tag: info.get("routing_instructions", "")
                for tag, info in registry.items()
                if info.get("routing_instructions", "")
            }

            # 3. Save defaults as new overrides
            from hecos.config import save_yaml
            from hecos.config.schemas.routing_schema import RoutingOverrides
            model = RoutingOverrides(overrides=defaults)
            if save_yaml(_routing_path, model):
                logger.info("[WebUI] Routing overrides reset to defaults.")
                return jsonify({"ok": True, "backup_created": True})
            return jsonify({"ok": False, "error": "Save failed after reset"}), 500
        except Exception as exc:
            logger.error(f"[WebUI] POST /hecos/config/routing/reset error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── GET current YAML as raw text (for backup display) ────────────────────
    @app.route("/hecos/config/routing/backup", methods=["GET"])
    def get_routing_backup_text():
        """Return the current routing_overrides.yaml as raw text for copy/paste backup."""
        try:
            if not os.path.exists(_routing_path):
                return jsonify({"yaml": ""}), 200
            with open(_routing_path, "r", encoding="utf-8") as f:
                content = f.read()
            return jsonify({"yaml": content})
        except Exception as exc:
            logger.error(f"[WebUI] GET /hecos/config/routing/backup error: {exc}")
            return jsonify({"error": str(exc)}), 500
