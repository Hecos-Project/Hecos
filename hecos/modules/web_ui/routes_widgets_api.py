"""
routes_widgets_api.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Widget Basic API Routes
Handles listing sidebar widgets and setting their global order.
─────────────────────────────────────────────────────────────────────────────
"""
import time
from flask import jsonify, request
from flask_login import login_required

# ── In-memory cache ───────────────────────────────────────────────────────────
_WIDGETS_CACHE: dict = {}  # {"data": [...], "ts": float}
_WIDGETS_CACHE_TTL = 30    # seconds

def invalidate_widgets_cache() -> None:
    """Clear the widgets list cache. Call after any widget/package state change."""
    _WIDGETS_CACHE.clear()
# ─────────────────────────────────────────────────────────────────────────────


def init_widget_api_routes(app, config_manager, _log, _get_config, _save_config):

    @app.route("/api/widgets", methods=["GET"])
    @login_required
    def api_get_widgets():
        """
        Returns all sidebar widgets with their current status.
        Results are cached in-memory (TTL: _WIDGETS_CACHE_TTL seconds).
        Response: { ok: true, widgets: [ {...manifest, plugin_active, visible, order_index } ] }
        """
        # ── Cache hit ─────────────────────────────────────────────────────────
        if _WIDGETS_CACHE.get("data") and (time.time() - _WIDGETS_CACHE.get("ts", 0)) < _WIDGETS_CACHE_TTL:
            return jsonify({"ok": True, "widgets": _WIDGETS_CACHE["data"], "cached": True})
        # ──────────────────────────────────────────────────────────────────────

        from hecos.core.system.extension_loader import get_all_widgets
        try:
            cfg = _get_config()
            widgets = get_all_widgets(config=cfg)

            # ── Save to cache ─────────────────────────────────────────────────
            _WIDGETS_CACHE["data"] = widgets
            _WIDGETS_CACHE["ts"]   = time.time()
            # ──────────────────────────────────────────────────────────────────

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
            invalidate_widgets_cache()  # order changed → invalidate
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Failed to set config"}), 500

