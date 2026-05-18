"""
routes_widgets_room.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Control Room Logic Routes
Handles the dashboard layout configuration (visible, spanning, order)
for the isolated iframes of the Control Room.
─────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify, request, make_response, render_template
from flask_login import login_required


def init_widget_room_routes(app, config_manager, _log, _get_config, _save_config):

    @app.route("/api/widgets/room", methods=["GET"])
    @login_required
    def api_render_room_widgets():
        """
        Returns the ordered room widget metadata list (ext_id, span, etc.).
        Shared by Module A & B to render the grid via JS. Uses context query param.
        """
        from hecos.core.system.extension_loader import get_all_widgets
        ctx = request.args.get("context", "sidebar")

        cfg = _get_config()
        all_widgets = get_all_widgets(config=cfg)
        
        # Load independent layouts
        if ctx == "standalone":
             room_layout = cfg.get("widgets", {}).get("home_layout", [])
        else:
             room_layout = cfg.get("widgets", {}).get("room_layout", [])

        _log.debug(f"[ROOM] /api/widgets/room?context={ctx} called — total widgets: {len(all_widgets)}")

        room_widgets = []
        for w in all_widgets:
            ext_id = w.get("extension_id", "?")
            prefs = cfg.get("widgets", {}).get("per_widget", {}).get(ext_id, {})
            # Read context-specific overrides from prefs, fallback to global
            room_visible = prefs.get(f"{ctx}_visible", w.get("room_visible", False))
            room_span = prefs.get(f"{ctx}_span", w.get("room_span", 1))
            room_theme = prefs.get("theme", w.get("theme", "default"))
            room_height = prefs.get(f"{ctx}_height", w.get("room_height", None))
            
            _log.debug(f"[ROOM] [{ctx}] widget={ext_id} visible={room_visible} span={room_span} theme={room_theme}")
            if room_visible:
                room_widgets.append({
                    **w,
                    "room_visible": True,
                    "room_span": room_span,
                    "room_height": room_height,
                    "theme": room_theme
                })

        # Sort by explicit layout order if defined
        if room_layout:
            order_map = {eid: i for i, eid in enumerate(room_layout)}
            room_widgets.sort(key=lambda ww: order_map.get(ww.get("extension_id", ""), 9999))

        _log.info(f"[ROOM] [{ctx}] Returning {len(room_widgets)} widgets")

        resp = jsonify({"ok": True, "widgets": room_widgets})
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


    @app.route("/api/widgets/room/<ext_id>/frame", methods=["GET"])
    @login_required
    def api_render_room_widget_frame(ext_id):
        """
        Returns the raw HTML document for a specific widget.
        Used as the src for iframes in the Control Room to isolate JS context.
        """
        from hecos.core.system.extension_loader import get_all_widgets
        from hecos.core.i18n.translator import t, get_translator

        cfg = _get_config()
        widgets = get_all_widgets(config=cfg)
        manifest = next((w for w in widgets if w["extension_id"] == ext_id), None)

        if not manifest:
            return "Widget not found", 404

        widget_theme = cfg.get("widgets", {}).get("per_widget", {}).get(ext_id, {}).get("theme", "default")
        if hasattr(widget_theme, 'value'):
            widget_theme = widget_theme.value

        trans = get_translator().get_translations()

        html = render_template(
            "modules/control_room_widget_frame.html",
            ext_id=ext_id,
            ext_manifest=manifest,
            widget_theme=widget_theme,
            zconfig=cfg,
            translations=trans,
            t=t
        )
        resp = make_response(html)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


    @app.route("/api/widgets/<ext_id>/room_visible", methods=["POST"])
    @login_required
    def api_set_widget_room_visible(ext_id):
        ctx = request.args.get("context", "sidebar")
        data = request.get_json(silent=True) or {}
        if "visible" not in data:
            return jsonify({"ok": False, "error": "'visible' field required"}), 400
        visible = bool(data["visible"])
        _log.info(f"WIDGETS [{ctx}]: Room visibility [{ext_id}] -> {visible}")
        # Always save specifically to the context
        res = config_manager.set(visible, "widgets", "per_widget", ext_id, f"{ctx}_visible")
        # For backward compatibility / safety, if it's sidebar, we can also set room_visible
        if res and ctx == "sidebar":
             config_manager.set(visible, "widgets", "per_widget", ext_id, "room_visible")
             if visible:
                 config_manager.set(False, "widgets", "per_widget", ext_id, "visible")
        if res:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, f"{ctx}_visible": visible})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/<ext_id>/room_span", methods=["POST"])
    @login_required
    def api_set_widget_room_span(ext_id):
        ctx = request.args.get("context", "sidebar")
        data = request.get_json(silent=True) or {}
        span = data.get("span", 1)
        if span not in (1, 2):
            return jsonify({"ok": False, "error": "span must be 1 or 2"}), 400
        _log.info(f"WIDGETS [{ctx}]: Room span [{ext_id}] -> {span}")
        res = config_manager.set(span, "widgets", "per_widget", ext_id, f"{ctx}_span")
        if res and ctx == "sidebar":
             config_manager.set(span, "widgets", "per_widget", ext_id, "room_span")
        if res:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, f"{ctx}_span": span})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/<ext_id>/room_height", methods=["POST"])
    @login_required
    def api_set_widget_room_height(ext_id):
        ctx = request.args.get("context", "sidebar")
        data = request.get_json(silent=True) or {}
        height = data.get("height")  # None is valid (resets to default)
        _log.info(f"WIDGETS [{ctx}]: Room height [{ext_id}] -> {height}")
        res = config_manager.set(height, "widgets", "per_widget", ext_id, f"{ctx}_height")
        if res and ctx == "sidebar":
             config_manager.set(height, "widgets", "per_widget", ext_id, "room_height")
        if res:
            _save_config()
            return jsonify({"ok": True, "ext_id": ext_id, f"{ctx}_height": height})
        return jsonify({"ok": False, "error": "Failed to update config"}), 500


    @app.route("/api/widgets/room/layout", methods=["PATCH"])
    @login_required
    def api_set_room_layout():
        ctx = request.args.get("context", "sidebar")
        data = request.get_json(silent=True) or {}
        layout = data.get("layout")
        if not isinstance(layout, list):
            return jsonify({"ok": False, "error": "'layout' must be an array of ext_ids"}), 400
        _log.info(f"WIDGETS [{ctx}]: Saving room layout -> {layout}")
        
        if ctx == "standalone":
            res = config_manager.set(layout, "widgets", "home_layout")
        else:
            res = config_manager.set(layout, "widgets", "room_layout")
            
        if res:
            _save_config()
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": "Failed to update layout"}), 500
