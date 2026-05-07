"""
MODULE: Reminder Store
DESCRIPTION: SQLite-based persistence layer for reminders.
             DB: memory/reminders.db
             All operations are thread-safe via SQLite WAL mode.
"""

import sqlite3
import os
import json
import uuid
from datetime import datetime
from hecos.core.logging import logger

# ── Path resolution ───────────────────────────────────────────────────────────
def _get_db_path() -> str:
    """Resolves memory/reminders.db relative to the project root."""
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.normpath(os.path.join(_here, "..", "..", ".."))
    mem_dir = os.path.join(_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return os.path.join(mem_dir, "reminders.db")


# ── Schema ────────────────────────────────────────────────────────────────────
_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS reminders (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    when_iso    TEXT,
    cron_expr   TEXT,
    repeat      INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL,
    interactive INTEGER,         -- NULL=use default, 1=interactive, 0=simple
    mode        TEXT             -- NULL=use default, 'voice', 'ringtone', 'both'
);
"""

_MIGRATE_SQL = [
    "ALTER TABLE reminders ADD COLUMN interactive INTEGER",
    "ALTER TABLE reminders ADD COLUMN mode TEXT",
]


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_CREATE_SQL)
    # Run any pending migrations (safe: silently ignore if already done)
    for stmt in _MIGRATE_SQL:
        try:
            conn.execute(stmt)
        except Exception:
            pass
    conn.commit()
    return conn


# ── CRUD ──────────────────────────────────────────────────────────────────────

def add(title: str, when_iso: str = None, cron_expr: str = None,
        repeat: bool = False, interactive: bool = None, mode: str = None) -> dict:
    """
    Inserts a new reminder and returns it as a dict.
    :param interactive: True=interactive snooze, False=simple, None=use system default.
    :param mode: 'voice', 'ringtone', 'both', or None for system default.
    """
    reminder = {
        "id":          str(uuid.uuid4()),
        "title":       title,
        "when_iso":    when_iso,
        "cron_expr":   cron_expr,
        "repeat":      1 if repeat else 0,
        "status":      "active",
        "created_at":  datetime.now().isoformat(),
        "interactive": (1 if interactive else (0 if interactive is False else None)),
        "mode":        mode,
    }
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO reminders (id, title, when_iso, cron_expr, repeat, status, created_at, interactive, mode) "
                "VALUES (:id, :title, :when_iso, :cron_expr, :repeat, :status, :created_at, :interactive, :mode)",
                reminder
            )
        logger.debug("REMINDER", f"Added: [{reminder['id']}] '{title}' interactive={interactive}")
    except Exception as e:
        logger.error(f"[REMINDER] store.add error: {e}")
    return reminder


def get_all(status_filter: str = None) -> list:
    """
    Returns all reminders, optionally filtered by status.
    :param status_filter: 'active', 'fired', 'cancelled', 'snoozed', or None for all.
    """
    try:
        with _get_conn() as conn:
            if status_filter:
                rows = conn.execute(
                    "SELECT * FROM reminders WHERE status = ? ORDER BY created_at ASC",
                    (status_filter,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM reminders ORDER BY created_at ASC"
                ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[REMINDER] store.get_all error: {e}")
        return []


def get_by_id(reminder_id: str) -> dict | None:
    """Returns a single reminder by ID, or None if not found."""
    try:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
            ).fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"[REMINDER] store.get_by_id error: {e}")
        return None


def update_status(reminder_id: str, status: str) -> bool:
    """Updates the status of a reminder. Returns True on success."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE reminders SET status = ? WHERE id = ?",
                (status, reminder_id)
            )
        logger.debug("REMINDER", f"Status updated: [{reminder_id}] → {status}")
        return True
    except Exception as e:
        logger.error(f"[REMINDER] store.update_status error: {e}")
        return False


def update_when(reminder_id: str, new_iso: str) -> bool:
    """Updates the scheduled datetime of a reminder (used for snooze)."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE reminders SET when_iso = ?, status = 'active' WHERE id = ?",
                (new_iso, reminder_id)
            )
        return True
    except Exception as e:
        logger.error(f"[REMINDER] store.update_when error: {e}")
        return False


def update_interactive(reminder_id: str, interactive: bool) -> bool:
    """Sets the per-reminder interactive flag (overrides system default)."""
    try:
        val = 1 if interactive else 0
        with _get_conn() as conn:
            conn.execute(
                "UPDATE reminders SET interactive = ? WHERE id = ?",
                (val, reminder_id)
            )
        return True
    except Exception as e:
        logger.error(f"[REMINDER] store.update_interactive error: {e}")
        return False


def cancel(reminder_id: str) -> bool:
    """Marks a reminder as cancelled. Returns True on success."""
    return update_status(reminder_id, "cancelled")


def clear_history() -> bool:
    """Deletes all 'fired' and 'cancelled' reminders from the history."""
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM reminders WHERE status IN ('fired', 'cancelled')")
        logger.debug("REMINDER", "Deleted historical reminders.")
        return True
    except Exception as e:
        logger.error(f"[REMINDER] store.clear_history error: {e}")
        return False


def get_upcoming(n: int = 5) -> list:
    """Returns the next N active reminders sorted by scheduled time."""
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE status = 'active' "
                "ORDER BY when_iso ASC NULLS LAST LIMIT ?",
                (n,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[REMINDER] store.get_upcoming error: {e}")
        return []
