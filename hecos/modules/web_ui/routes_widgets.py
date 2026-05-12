"""
Widget Manager API Routes
Provides REST endpoints to list, reorder, and toggle widget visibility.
Registered in server.py alongside other route modules.
"""
import os
from hecos.core.logging import logger


def init_widget_routes(app, config_manager, logger_ref=None):
    """Registers all /api/widgets/* routes."""
    from flask import jsonify, request
    from flask_login import login_required

    _log = logger_ref or logger

    def _get_config():
        return config_manager.config if config_manager else {}

    def _save_config():
        """Saves current config and broadcasts a refresh signal."""
        res = config_manager.save()
        if res:
            try:
                from .server import get_state_manager
                sm = get_state_manager()
                if sm:
                    sm.add_event("widgets_refresh")
            except Exception as e:
                _log.warning(f"[Widgets] Failed to trigger SSE refresh: {e}")
        return res

    # ── GET /api/widgets ────────────────────────────────────────────────────────
    @app.route("/api/widgets", methods=["GET"])
    @login_required
    def api_get_widgets():
        """
        Returns all sidebar widgets with their current status.
        Response: { ok: true, widgets: [ {...manifest, plugin_active, visible, order_index } ] }
        """
        from hecos.core.system.extension_loader import get_all_widgets
        try:
            cfg = _get_config()
            widgets = get_all_widgets(config=cfg)
            return jsonify({"ok": True, "widgets": widgets})
        except Exception as e:
            _log.warning(f"[Widgets] GET /api/widgets error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /api/widgets/order ─────────────────────────────────────────────────
    @app.route("/api/widgets/order", methods=["POST"])
    @login_required
    def api_set_widget_order():
        data = request.get_json(silent=True) or {}
        order = data.get("order")
        if not isinstance(order, list):
            return jsonify({"ok": False, "error": "'order' must be a list"}), 400

        # Debug log
        _log.info(f"WIDGETS: Saving new order -> {order}")
        
        res = config_manager.set(order, "widgets", "sidebar_order")
        if res:
            ok = _save_config()
            _log.info(f"WIDGETS: Save result: {ok}")
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Failed to set config"}), 500

    # ── POST /api/widgets/<ext_id>/visible ──────────────────────────────────────
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
            ok = _save_config()
            _log.info(f"WIDGETS: Save result for [{ext_id}]: {ok}")
            return jsonify({"ok": True, "ext_id": ext_id, "visible": visible})
        
        _log.warning(f"WIDGETS: Failed to set visibility for [{ext_id}]")
        return jsonify({"ok": False, "error": "Failed to update config"}), 500

    # ── POST /api/widgets/status-collapsed ──────────────────────────────────────
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

    # ── POST /api/widgets/audio-collapsed ───────────────────────────────────────
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

    # ── GET /api/widgets/render ────────────────────────────────────────────────
    @app.route("/api/widgets/render", methods=["GET"])
    @login_required
    def api_render_widgets():
        """
        Returns the rendered HTML of the sidebar widgets.
        Used for real-time updates without full page reload.
        """
        from flask import render_template
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
