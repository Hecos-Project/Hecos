"""
MODULE: Calendar Backup API
DESCRIPTION: Provides /api/calendar/backup and /api/calendar/restore routes for Global Backup.
"""

from flask import jsonify, request
from hecos.core.logging import logger
import uuid
from datetime import datetime

def register_backup_routes(app):
    """Registers the backup routes for the calendar plugin."""

    @app.route("/api/calendar/backup", methods=["GET"], endpoint="mbkp_calendar_backup_pkg")
    def calendar_backup():
        """Esporta tutti gli eventi del calendario come JSON."""
        try:
            from .. import store
            with store._get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM calendar_events ORDER BY start_iso ASC"
                ).fetchall()
            events = [dict(r) for r in rows]
            return jsonify({"ok": True, "count": len(events), "data": events})
        except Exception as e:
            logger.error(f"[CALENDAR BACKUP] calendar_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/calendar/restore", methods=["POST"], endpoint="mbkp_calendar_restore_pkg")
    def calendar_restore():
        """
        Ripristina eventi calendario da JSON.
        Body: { data: [...], mode: "duplicate"|"replace" }
        """
        try:
            from .. import store
            
            body = request.get_json(force=True) or {}
            events = body.get("data", [])
            mode   = body.get("mode", "duplicate")

            if not isinstance(events, list):
                return jsonify({"ok": False, "error": "data must be a list"}), 400

            with store._get_conn() as conn:
                if mode == "replace":
                    conn.execute("DELETE FROM calendar_events")

                imported = 0
                for ev in events:
                    try:
                        new_id = str(uuid.uuid4())
                        conn.execute(
                            """INSERT OR IGNORE INTO calendar_events
                               (id, title, start_iso, end_iso, all_day, color, notes,
                                linked_reminder_id, interactive, external_id, sync_source, created_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                new_id,
                                ev.get("title", "Evento"),
                                ev.get("start_iso", ""),
                                ev.get("end_iso"),
                                int(ev.get("all_day", 0)),
                                ev.get("color"),
                                ev.get("notes"),
                                ev.get("linked_reminder_id"),
                                int(ev.get("interactive", 0)),
                                ev.get("external_id"),
                                ev.get("sync_source"),
                                ev.get("created_at") or datetime.now().isoformat(),
                            )
                        )
                        imported += 1
                    except Exception as row_e:
                        logger.error(f"[CALENDAR BACKUP] row error: {row_e}")

            return jsonify({"ok": True, "imported": imported})
        except Exception as e:
            logger.error(f"[CALENDAR BACKUP] calendar_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
