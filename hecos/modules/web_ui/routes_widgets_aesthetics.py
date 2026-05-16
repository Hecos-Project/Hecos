"""
routes_widgets_aesthetics.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Widget Aesthetics Routes
Handles CSS overrides, visual themes, and resets for widgets.
─────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify, request
from flask_login import login_required


def init_widget_aesthetics_routes(app, config_manager, _log, _get_config, _save_config):

    @app.route("/api/widgets/<ext_id>/theme", methods=["POST"])
    @login_required
    def api_set_widget_theme(ext_id):
        data = request.get_json(silent=True) or {}
        theme = data.get("theme", "default")
        _log.info(f"WIDGETS: Room theme [{ext_id}] -> {theme}")
        res = config_manager.set(theme, "widgets", "per_widget", ext_id, "theme")
        if res:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, "theme": theme})
        return jsonify({"ok": False, "error": "Failed to update theme"}), 500


    @app.route("/api/widgets/<ext_id>/aesthetics", methods=["POST"])
    @login_required
    def api_set_widget_aesthetics(ext_id):
        """Sets bg_color and bg_image for a specific widget."""
        data = request.get_json(silent=True) or {}
        bg_color = data.get("bg_color")
        bg_image = data.get("bg_image")
        
        _log.info(f"WIDGETS: Aesthetics [{ext_id}] -> color={bg_color}, image={bg_image}")
        
        # We set them individually but save once
        res_c = config_manager.set(bg_color, "widgets", "per_widget", ext_id, "bg_color")
        res_i = config_manager.set(bg_image, "widgets", "per_widget", ext_id, "bg_image")
        
        if res_c and res_i:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, "bg_color": bg_color, "bg_image": bg_image})
            
        return jsonify({"ok": False, "error": "Failed to update aesthetics"}), 500


    @app.route("/api/widgets/<ext_id>/aesthetics/reset", methods=["POST"])
    @login_required
    def api_reset_widget_aesthetics(ext_id):
        """Clears all aesthetic overrides (theme, color, image) for a widget."""
        _log.info(f"WIDGETS: Resetting aesthetics for [{ext_id}]")
        
        # We clear the specific keys by setting them to "" (empty string) to satisfy Pydantic schema
        res1 = config_manager.set("default", "widgets", "per_widget", ext_id, "theme")
        res2 = config_manager.set("", "widgets", "per_widget", ext_id, "bg_color")
        res3 = config_manager.set("", "widgets", "per_widget", ext_id, "bg_image")
        
        if res1 and res2 and res3:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id})
            
        return jsonify({"ok": False, "error": "Failed to reset aesthetics"}), 500
