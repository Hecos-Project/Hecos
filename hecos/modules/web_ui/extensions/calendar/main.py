"""
MODULE: Calendar WebUI Extension — Backend Routes
DESCRIPTION: Flask REST API for the calendar sidebar widget and config panel.
             Registered at boot via extension_loader (eager_load: true).
"""

import os
from hecos.core.logging import logger


def init_routes(app, root_dir: str = None):
    """
    Registers Calendar REST API routes under /api/ext/calendar.
    Called by extension_loader at WebUI boot.
    """
    from flask import request, jsonify, render_template
    from flask_login import login_required

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_store():
        try:
            from hecos.plugins.calendar import store
            return store
        except ImportError:
            return None

    # ── Static assets ──────────────────────────────────────────────────────────
    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/ext/calendar/static/<path:filename>")
    def calendar_static(filename):
        from flask import send_from_directory
        return send_from_directory(_static_dir, filename)

    # ── GET /api/ext/calendar/events ──────────────────────────────────────────
    @app.route("/api/ext/calendar/events", methods=["GET"])
    @login_required
    def calendar_get_events():
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Calendar plugin unavailable"}), 503

        # FullCalendar passes `start` and `end` as query params for range fetching
        start_param = request.args.get("start")
        end_param = request.args.get("end")

        try:
            if start_param and end_param:
                events = store.get_range(start_param, end_param)
            else:
                events = store.get_all()

            # Convert to FullCalendar event format
            fc_events = []
            for ev in events:
                fc_ev = {
                    "id":       ev["id"],
                    "title":    ev["title"],
                    "start":    ev["start_iso"],
                    "allDay":   ev["all_day"],
                }
                if ev.get("end_iso"):
                    fc_ev["end"] = ev["end_iso"]
                if ev.get("color"):
                    fc_ev["color"] = ev["color"]
                if ev.get("notes"):
                    fc_ev["extendedProps"] = {"notes": ev["notes"]}
                fc_events.append(fc_ev)

            return jsonify({"ok": True, "events": fc_events})
        except Exception as e:
            logger.debug("CALENDAR", f"GET /events error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET /api/ext/calendar/holidays ────────────────────────────────────────
    @app.route("/api/ext/calendar/holidays", methods=["GET"])
    @login_required
    def calendar_get_holidays():
        try:
            import holidays
        except ImportError:
            return jsonify([])

        start_param = request.args.get("start")
        end_param = request.args.get("end")
        
        from datetime import datetime
        years = []
        if start_param and end_param:
            try:
                y1 = datetime.fromisoformat(start_param[:10]).year
                y2 = datetime.fromisoformat(end_param[:10]).year
                years = list(range(y1, y2 + 1))
            except:
                years = [datetime.now().year]
        else:
            years = [datetime.now().year]

        from hecos.core.config import get_config_manager
        cfg_mgr = get_config_manager()
        country = "IT"
        try:
            # Depending on core config layout, extensions conf is usually inside "extensions"
            c = cfg_mgr.get_extension_config("calendar") or {}
            tmp = c.get("calendar_country")
            if not tmp:
                c2 = getattr(cfg_mgr, "config", {}).get("extensions", {}).get("calendar", {})
                tmp = c2.get("calendar_country")
            if tmp:
                country = str(tmp).upper()
        except:
            pass

        try:
            country_holidays = holidays.country_holidays(country, years=years)
            fc_events = []
            for dt, name in sorted(country_holidays.items()):
                fc_events.append({
                    "title": name,
                    "start": dt.isoformat(),
                    "allDay": True,
                    "display": "list-item",
                    "classNames": ["cal-holiday-event"]
                })
            return jsonify(fc_events)
        except Exception as e:
            logger.debug("CALENDAR", f"Holidays error: {e}")
            return jsonify([])

    # ── POST /api/ext/calendar/events ─────────────────────────────────────────
    @app.route("/api/ext/calendar/events", methods=["POST"])
    @login_required
    def calendar_create_event():
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Calendar plugin unavailable"}), 503

        data = request.get_json(silent=True) or {}
        title = (data.get("title") or "").strip()
        start = (data.get("start") or "").strip()
        end = (data.get("end") or "").strip() or None
        all_day = bool(data.get("allDay", False))
        color = (data.get("color") or "").strip() or None
        notes = (data.get("notes") or "").strip() or None

        if not title or not start:
            return jsonify({"ok": False, "error": "title and start are required"}), 400

        try:
            event = store.add(
                title=title, start_iso=start, end_iso=end,
                all_day=all_day, color=color, notes=notes
            )
            return jsonify({"ok": True, "event": event})
        except Exception as e:
            logger.debug("CALENDAR", f"POST /events error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── PUT /api/ext/calendar/events/<id> ─────────────────────────────────────
    @app.route("/api/ext/calendar/events/<eid>", methods=["PUT"])
    @login_required
    def calendar_update_event(eid):
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Calendar plugin unavailable"}), 503

        data = request.get_json(silent=True) or {}
        kwargs = {}
        for field in ("title", "start_iso", "end_iso", "all_day", "color", "notes"):
            # Map FullCalendar camelCase to snake_case
            fc_key = {"start_iso": "start", "end_iso": "end", "all_day": "allDay"}.get(field, field)
            if fc_key in data:
                kwargs[field] = data[fc_key]
        # Also accept snake_case from our own widget
        for field in ("title", "start_iso", "end_iso", "all_day", "color", "notes"):
            if field in data:
                kwargs[field] = data[field]

        try:
            updated = store.update(eid, **kwargs)
            return jsonify({"ok": updated})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── DELETE /api/ext/calendar/events/<id> ──────────────────────────────────
    @app.route("/api/ext/calendar/events/<eid>", methods=["DELETE"])
    @login_required
    def calendar_delete_event(eid):
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Calendar plugin unavailable"}), 503

        try:
            deleted = store.delete(eid)
            return jsonify({"ok": deleted})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET /api/ext/calendar/upcoming?n=3 ────────────────────────────────────
    @app.route("/api/ext/calendar/upcoming", methods=["GET"])
    @login_required
    def calendar_upcoming():
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Calendar plugin unavailable"}), 503
        try:
            n = int(request.args.get("n", 3))
            events = store.get_upcoming(n)
            return jsonify({"ok": True, "events": events})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    logger.info("CALENDAR", "📅 Calendar WebUI routes registered.")
