"""
routes_widgets_api.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Widget Basic API Routes
Handles listing sidebar widgets and setting their global order.
─────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify, request
from flask_login import login_required


def init_widget_api_routes(app, config_manager, _log, _get_config, _save_config):

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
