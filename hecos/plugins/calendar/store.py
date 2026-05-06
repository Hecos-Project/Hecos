"""
MODULE: Calendar Store
DESCRIPTION: SQLite-based persistence layer for calendar events.
             DB: memory/calendar.db
             Thread-safe via WAL mode.
"""

import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from hecos.core.logging import logger

# ── Path resolution ────────────────────────────────────────────────────────────
def _get_db_path() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.normpath(os.path.join(_here, "..", "..", ".."))
    mem_dir = os.path.join(_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return os.path.join(mem_dir, "calendar.db")


# ── Schema ─────────────────────────────────────────────────────────────────────
_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS calendar_events (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    start_iso   TEXT NOT NULL,
    end_iso     TEXT,
    all_day     INTEGER NOT NULL DEFAULT 0,
    color       TEXT,
    notes       TEXT,
    created_at  TEXT NOT NULL
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_CREATE_SQL)
    conn.commit()
    return conn


def _row_to_dict(row) -> dict:
    d = dict(row)
    d["all_day"] = bool(d.get("all_day", 0))
    return d


# ── CRUD ───────────────────────────────────────────────────────────────────────

def add(title: str, start_iso: str, end_iso: str = None, all_day: bool = False,
        color: str = None, notes: str = None) -> dict:
    """Add a new calendar event. Returns the created event dict."""
    eid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO calendar_events (id, title, start_iso, end_iso, all_day, color, notes, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (eid, title, start_iso, end_iso, int(all_day), color, notes, now)
        )
        conn.commit()
        logger.debug("CALENDAR", f"Event created: [{eid}] '{title}' @ {start_iso}")
        return {
            "id": eid, "title": title, "start_iso": start_iso, "end_iso": end_iso,
            "all_day": all_day, "color": color, "notes": notes, "created_at": now
        }
    finally:
        conn.close()


def get_all() -> list:
    """Return all events ordered by start time."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM calendar_events ORDER BY start_iso ASC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_upcoming(n: int = 10) -> list:
    """Return the next N events from now, ordered by start time."""
    now = datetime.utcnow().isoformat()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM calendar_events WHERE start_iso >= ? ORDER BY start_iso ASC LIMIT ?",
            (now, n)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_range(start_iso: str, end_iso: str) -> list:
    """Return events overlapping with a given date range (for FullCalendar feed)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM calendar_events WHERE start_iso < ? AND (end_iso > ? OR (end_iso IS NULL AND start_iso >= ?)) ORDER BY start_iso ASC",
            (end_iso, start_iso, start_iso)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_by_id(event_id: str) -> dict | None:
    """Return a single event by ID (or first 8-char prefix)."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM calendar_events WHERE id = ? OR SUBSTR(id,1,8) = ?",
            (event_id, event_id)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def delete(event_id: str) -> bool:
    """Delete an event by ID or prefix. Returns True if deleted."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM calendar_events WHERE id = ? OR SUBSTR(id,1,8) = ?",
            (event_id, event_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update(event_id: str, **kwargs) -> bool:
    """Update specific fields of an event. Returns True if updated."""
    allowed = {"title", "start_iso", "end_iso", "all_day", "color", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    conn = _get_conn()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [event_id, event_id]
        cur = conn.execute(
            f"UPDATE calendar_events SET {set_clause} WHERE id = ? OR SUBSTR(id,1,8) = ?",
            vals
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
