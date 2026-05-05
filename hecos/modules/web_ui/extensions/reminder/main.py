"""
MODULE: Reminder WebUI Extension — Backend Routes
DESCRIPTION: Flask REST API for the sidebar widget and config panel.
             Registered at boot via extension_loader (eager_load: true).
"""

import os
from hecos.core.logging import logger


def init_routes(app, root_dir: str = None):
    """
    Registers Reminder REST API routes under /api/ext/reminder.
    Called by extension_loader at WebUI boot.
    """
    from flask import request, jsonify, render_template
    from flask_login import login_required

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_plugin():
        """Lazy-imports the reminder plugin tools singleton."""
        try:
            from hecos.plugins.reminder.main import tools
            return tools
        except ImportError:
            return None

    def _get_store():
        try:
            from hecos.plugins.reminder import store
            return store
        except ImportError:
            return None

    def _get_scheduler():
        try:
            from hecos.plugins.reminder import scheduler
            return scheduler
        except ImportError:
            return None

    # ── Static assets ─────────────────────────────────────────────────────────
    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/ext/reminder/static/<path:filename>")
    def reminder_static(filename):
        from flask import send_from_directory
        return send_from_directory(_static_dir, filename)

    # ── GET /api/ext/reminder — upcoming reminders for sidebar ────────────────
    @app.route("/api/ext/reminder", methods=["GET"])
    @login_required
    def reminder_get():
        """Returns the next N active reminders (for sidebar widget)."""
        n = int(request.args.get("n", 5))
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Reminder plugin not available"}), 503
        reminders = store.get_upcoming(n)
        return jsonify({"ok": True, "reminders": reminders})

    # ── GET /api/ext/reminder/all — full list ─────────────────────────────────
    @app.route("/api/ext/reminder/all", methods=["GET"])
    @login_required
    def reminder_get_all():
        """Returns all reminders (for the Config tab panel)."""
        store = _get_store()
        if not store:
            return jsonify({"ok": False, "error": "Reminder plugin not available"}), 503
        status_filter = request.args.get("status", None)
        reminders = store.get_all(status_filter=status_filter)
        return jsonify({"ok": True, "reminders": reminders})

    # ── POST /api/ext/reminder — quick-add from sidebar ───────────────────────
    @app.route("/api/ext/reminder", methods=["POST"])
    @login_required
    def reminder_add():
        """
        Quick-add reminder from the sidebar widget.
        Body: { title: str, when: str, repeat?: str }
        """
        data  = request.get_json(force=True) or {}
        title = (data.get("title") or "").strip()
        when  = (data.get("when")  or "").strip()
        rep   = (data.get("repeat") or "").strip() or None

        if not title or not when:
            return jsonify({"ok": False, "error": "title and when are required"}), 400

        plugin = _get_plugin()
        if not plugin:
            return jsonify({"ok": False, "error": "Reminder plugin not loaded"}), 503

        result = plugin.set_reminder(title=title, when=when, repeat=rep)
        success = result.startswith("✅")
        logger.debug("REMINDER_EXT", f"Quick-add: '{title}' @ '{when}' → ok={success}")
        return jsonify({"ok": success, "message": result})

    # ── DELETE /api/ext/reminder/<id> — cancel ────────────────────────────────
    @app.route("/api/ext/reminder/<reminder_id>", methods=["DELETE"])
    @login_required
    def reminder_cancel(reminder_id):
        """Cancels (deletes) a reminder by ID."""
        plugin = _get_plugin()
        if not plugin:
            return jsonify({"ok": False, "error": "Reminder plugin not loaded"}), 503
        result = plugin.cancel_reminder(reminder_id)
        return jsonify({"ok": "❌" not in result, "message": result})

    # ── POST /api/ext/reminder/<id>/snooze — snooze ───────────────────────────
    @app.route("/api/ext/reminder/<reminder_id>/snooze", methods=["POST"])
    @login_required
    def reminder_snooze(reminder_id):
        """Snoozes a reminder. Body: { minutes?: int } — default 15."""
        data    = request.get_json(force=True) or {}
        minutes = int(data.get("minutes", 15))
        plugin  = _get_plugin()
        if not plugin:
            return jsonify({"ok": False, "error": "Reminder plugin not loaded"}), 503
        result = plugin.snooze_reminder(reminder_id, minutes)
        return jsonify({"ok": "❌" not in result, "message": result})

    # ── GET /hecos/config/reminder — config tab page ──────────────────────────
    @app.route("/hecos/config/reminder")
    @login_required
    def reminder_config_page():
        """Serves the Reminder config/management page."""
        store = _get_store()
        reminders = store.get_all() if store else []
        sched = _get_scheduler()
        sched_status = sched.get_status() if sched else {}
        try:
            return render_template(
                "reminder_config.html",
                reminders=reminders,
                scheduler_status=sched_status
            )
        except Exception as e:
            return (
                f"<h2>🔔 Reminder Config</h2>"
                f"<p>Template not found: {e}</p>"
                f"<pre>{reminders}</pre>"
            ), 200

    logger.debug("REMINDER_EXT", "Reminder extension routes registered.")
