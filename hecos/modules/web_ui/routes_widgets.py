"""
Widget Manager API Routes
Provides REST endpoints to list, reorder, and toggle widget visibility.
Includes Control Room grid layout endpoints (room_visible, room_span, room/layout).
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
        import sys
        print(f"[DEBUG-WIDGETS] save() result: {res}", file=sys.stderr)
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

    # ── GET /api/widgets/room ──────────────────────────────────────────────────
    @app.route("/api/widgets/room", methods=["GET"])
    @login_required
    def api_render_room_widgets():
        """
        Returns the ordered room widget metadata list (ext_id, span, etc.).
        Shared by Module A & B to render the grid via JS.
        """
        from hecos.core.system.extension_loader import get_all_widgets
        from hecos.core.i18n.translator import t

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        per_widget = cfg.get("widgets", {}).get("per_widget", {})
        room_layout = cfg.get("widgets", {}).get("room_layout", [])

        _log.debug(f"[ROOM] /api/widgets/room called — total widgets discovered: {len(all_widgets)}")

        # Build room widgets — only those with room_visible = True
        # Note: room_visible is already in the enriched dict from get_all_widgets
        room_widgets = []
        for w in all_widgets:
            ext_id = w.get("extension_id", "?")
            room_visible = w.get("room_visible", False)
            room_span = w.get("room_span", 1)
            room_theme = w.get("theme", "default")
            _log.debug(f"[ROOM]   widget={ext_id} room_visible={room_visible} room_span={room_span} theme={room_theme}")
            if room_visible:
                room_widgets.append({
                    **w,
                    "room_visible": True,
                    "room_span": room_span,
                    "theme": room_theme
                })

        # Sort by explicit layout order if defined
        if room_layout:
            order_map = {eid: i for i, eid in enumerate(room_layout)}
            room_widgets.sort(key=lambda ww: order_map.get(ww.get("extension_id", ""), 9999))

        _log.info(f"[ROOM] Returning {len(room_widgets)} room widgets")

        resp = jsonify({"ok": True, "widgets": room_widgets})
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    # ── GET /api/widgets/room/<ext_id>/frame ────────────────────────────────────
    @app.route("/api/widgets/room/<ext_id>/frame", methods=["GET"])
    @login_required
    def api_render_room_widget_frame(ext_id):
        """
        Returns the raw HTML document for a specific widget.
        Used as the src for iframes in the Control Room to isolate JS context.
        """
        from flask import render_template, make_response
        from hecos.core.system.extension_loader import get_all_widgets
        from hecos.core.i18n.translator import t, get_translator

        cfg = _get_config()
        widgets = get_all_widgets(config=cfg)
        manifest = next((w for w in widgets if w["extension_id"] == ext_id), None)

        if not manifest:
            return "Widget not found", 404

        trans = get_translator().get_translations()

        html = render_template(
            "modules/control_room_widget_frame.html",
            ext_id=ext_id,
            ext_manifest=manifest,
            zconfig=cfg,
            translations=trans,
            t=t
        )
        resp = make_response(html)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp



    # -- POST /api/widgets/<ext_id>/room_visible ----------------------------------
    @app.route("/api/widgets/<ext_id>/room_visible", methods=["POST"])
    @login_required
    def api_set_widget_room_visible(ext_id):
        data = request.get_json(silent=True) or {}
        if "visible" not in data:
            return jsonify({"ok": False, "error": "'visible' field required"}), 400
        visible = bool(data["visible"])
        _log.info(f"WIDGETS: Room visibility [{ext_id}] -> {visible}")
        res = config_manager.set(visible, "widgets", "per_widget", ext_id, "room_visible")
        if res:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, "room_visible": visible})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500

    # -- POST /api/widgets/<ext_id>/room_span -------------------------------------
    @app.route("/api/widgets/<ext_id>/room_span", methods=["POST"])
    @login_required
    def api_set_widget_room_span(ext_id):
        data = request.get_json(silent=True) or {}
        span = data.get("span", 1)
        if span not in (1, 2):
            return jsonify({"ok": False, "error": "span must be 1 or 2"}), 400
        _log.info(f"WIDGETS: Room span [{ext_id}] -> {span}")
        res = config_manager.set(span, "widgets", "per_widget", ext_id, "room_span")
        if res:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, "room_span": span})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500

    # -- POST /api/widgets/<ext_id>/theme -----------------------------------------
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

    # -- PATCH /api/widgets/room/layout -------------------------------------------
    @app.route("/api/widgets/room/layout", methods=["PATCH"])
    @login_required
    def api_set_room_layout():
        data = request.get_json(silent=True) or {}
        layout = data.get("layout")
        if not isinstance(layout, list):
            return jsonify({"ok": False, "error": "'layout' must be an array of ext_ids"}), 400
        _log.info(f"WIDGETS: Saving room layout -> {layout}")
        res = config_manager.set(layout, "widgets", "room_layout")
        if res:
            _save_config()
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Failed to update layout"}), 500
