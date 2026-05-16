"""
routes_config_utils.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Configuration Utility Routes
Handles plugin registry reads and UI state persistence (panel sizes, etc.).
─────────────────────────────────────────────────────────────────────────────
"""
import os
import json
from flask import request, jsonify


def init_config_utils_routes(app, root_dir, logger):
    """Register utility config routes: plugin registry and UI state."""

    _state_file = os.path.join(root_dir, 'hecos', 'core', 'config', 'ui_state.json')

    @app.route("/api/plugins/registry", methods=["GET"])
    def get_plugin_registry():
        try:
            from hecos.core.system.module_state import REGISTRY_PATH
            if os.path.exists(REGISTRY_PATH):
                with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                    return jsonify(json.load(f))
            return jsonify({})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/webui/state', methods=['GET', 'POST'])
    def handle_ui_state():
        os.makedirs(os.path.dirname(_state_file), exist_ok=True)

        if request.method == 'POST':
            try:
                state = request.get_json()
                with open(_state_file, 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=4)
                return jsonify({"status": "success"})
            except Exception as e:
                logger.error(f"[WebUI] UI state save error: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        if os.path.exists(_state_file):
            try:
                with open(_state_file, 'r', encoding='utf-8') as f:
                    return jsonify(json.load(f))
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        return jsonify({})
