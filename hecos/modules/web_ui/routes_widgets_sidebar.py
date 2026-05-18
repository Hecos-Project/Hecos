"""
routes_widgets_sidebar.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Sidebar Management Routes
Handles global toggles for the sidebar (visible, audio-collapsed, etc.)
and HTML fragment rendering updates.
─────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify, request, render_template
from flask_login import login_required


def init_widget_sidebar_routes(app, config_manager, _log, _get_config, _save_config):

    @app.route("/api/widgets/<ext_id>/visible", methods=["POST"])
    @login_required
    def api_set_widget_visible(ext_id):
        data = request.get_json(silent=True) or {}
        if "visible" not in data:
            return jsonify({"ok": False, "error": "'visible' field required"}), 400

        visible = bool(data["visible"])
        _log.info(f"WIDGETS: Setting visibility for [{ext_id}] to {visible}")
        
        res = config_manager.set(visible, "widgets", "per_widget", ext_id, "visible")
        if res:
            # XOR: If enabling sidebar, disable room
            if visible:
                config_manager.set(False, "widgets", "per_widget", ext_id, "room_visible")
            
            ok = _save_config()
            _log.info(f"WIDGETS: Save result for [{ext_id}]: {ok}")
            return jsonify({"ok": True, "ext_id": ext_id, "visible": visible})
        
        _log.warning(f"WIDGETS: Failed to set visibility for [{ext_id}]")
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/status-collapsed", methods=["POST"])
    @login_required
    def api_set_status_collapsed():
        data = request.get_json(silent=True) or {}
        if "collapsed" not in data:
            return jsonify({"ok": False, "error": "'collapsed' field required"}), 400

        collapsed = bool(data["collapsed"])
        _log.info(f"WIDGETS: Setting status-collapsed to {collapsed}")
        
        res = config_manager.set(collapsed, "widgets", "sidebar_status_collapsed")
        if res:
            ok = _save_config()
            return jsonify({"ok": True, "collapsed": collapsed})
        
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/audio-collapsed", methods=["POST"])
    @login_required
    def api_set_audio_collapsed():
        data = request.get_json(silent=True) or {}
        if "collapsed" not in data:
            return jsonify({"ok": False, "error": "'collapsed' field required"}), 400

        collapsed = bool(data["collapsed"])
        _log.info(f"WIDGETS: Setting audio-collapsed to {collapsed}")
        
        res = config_manager.set(collapsed, "widgets", "sidebar_audio_collapsed")
        if res:
            ok = _save_config()
            return jsonify({"ok": True, "collapsed": collapsed})
        
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/sidebar-enabled", methods=["POST"])
    @login_required
    def api_set_sidebar_widgets_enabled():
        data = request.get_json(silent=True) or {}
        if "enabled" not in data:
            return jsonify({"ok": False, "error": "'enabled' field required"}), 400

        enabled = bool(data["enabled"])
        _log.info(f"WIDGETS: Setting sidebar_widgets_enabled to {enabled}")
        
        res = config_manager.set(enabled, "widgets", "sidebar_widgets_enabled")
        if res:
            ok = _save_config()
            return jsonify({"ok": True, "enabled": enabled})
        
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/render", methods=["GET"])
    @login_required
    def api_render_widgets():
        """
        Returns the rendered HTML of the sidebar widgets.
        Used for real-time updates without full page reload.
        """
        from hecos.core.system.extension_loader import get_sidebar_widgets
        from hecos.core.i18n.translator import t
        
        cfg = _get_config()
        widgets = get_sidebar_widgets(config=cfg)
        
        # Render the partial
        html = render_template("modules/chat_sidebar_widgets.html", 
                               sidebar_widgets=widgets, 
                               t=t)
        
        resp = jsonify({"ok": True, "html": html})
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
