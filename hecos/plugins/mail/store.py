"""
MODULE: Mail Store
DESCRIPTION: SQLite-based persistence layer for the Mail plugin.
             DB: hecos/memory/mail.db
             Tables: messages, attachments, drafts
             Thread-safe via WAL mode.
"""

import sqlite3
import os
import uuid
from datetime import datetime
from hecos.core.logging import logger


# ── Path resolution ────────────────────────────────────────────────────────────
def _get_db_path() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.normpath(os.path.join(_here, "..", ".."))  # hecos/
    mem_dir = os.path.join(_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return os.path.join(mem_dir, "mail.db")


# ── Schema ─────────────────────────────────────────────────────────────────────
_CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id               TEXT PRIMARY KEY,
    uid              INTEGER NOT NULL DEFAULT 0,
    folder           TEXT NOT NULL DEFAULT 'INBOX',
    subject          TEXT NOT NULL DEFAULT '',
    from_addr        TEXT NOT NULL DEFAULT '',
    to_addrs         TEXT NOT NULL DEFAULT '',
    cc               TEXT NOT NULL DEFAULT '',
    bcc              TEXT NOT NULL DEFAULT '',
    reply_to         TEXT NOT NULL DEFAULT '',
    body_text        TEXT NOT NULL DEFAULT '',
    body_html        TEXT NOT NULL DEFAULT '',
    date             TEXT NOT NULL DEFAULT '',
    flags            TEXT NOT NULL DEFAULT '',
    read             INTEGER NOT NULL DEFAULT 0,
    starred          INTEGER NOT NULL DEFAULT 0,
    thread_id        TEXT NOT NULL DEFAULT '',
    message_id_header TEXT NOT NULL DEFAULT '',
    in_reply_to      TEXT NOT NULL DEFAULT '',
    has_attachments  INTEGER NOT NULL DEFAULT 0,
    preview          TEXT NOT NULL DEFAULT '',
    synced_at        TEXT NOT NULL DEFAULT ''
);
"""

_CREATE_ATTACHMENTS = """
CREATE TABLE IF NOT EXISTS attachments (
    id           TEXT PRIMARY KEY,
    message_id   TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    filename     TEXT NOT NULL DEFAULT '',
    size         INTEGER NOT NULL DEFAULT 0,
    content_type TEXT NOT NULL DEFAULT 'application/octet-stream',
    local_path   TEXT NOT NULL DEFAULT ''
);
"""

_CREATE_DRAFTS = """
CREATE TABLE IF NOT EXISTS drafts (
    id         TEXT PRIMARY KEY,
    to_addrs   TEXT NOT NULL DEFAULT '',
    cc         TEXT NOT NULL DEFAULT '',
    bcc        TEXT NOT NULL DEFAULT '',
    subject    TEXT NOT NULL DEFAULT '',
    body       TEXT NOT NULL DEFAULT '',
    is_html    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.executescript(_CREATE_MESSAGES + _CREATE_ATTACHMENTS + _CREATE_DRAFTS)
    conn.commit()
    return conn


def _row_to_dict(row) -> dict:
    return dict(row)


# ── Message CRUD ───────────────────────────────────────────────────────────────

def upsert_message(data: dict) -> dict:
    """Insert or update a message by its message_id_header (dedup) or id."""
    conn = _get_conn()
    try:
        now = datetime.utcnow().isoformat()
        mid = data.get("id") or str(uuid.uuid4())

        # Dedup by message_id_header
        mid_header = data.get("message_id_header", "")
        if mid_header:
            existing = conn.execute(
                "SELECT id FROM messages WHERE message_id_header = ?", (mid_header,)
            ).fetchone()
            if existing:
                mid = existing[0]

        preview = data.get("preview") or data.get("body_text", "")[:200].replace("\n", " ")

        conn.execute("""
            INSERT INTO messages
              (id, uid, folder, subject, from_addr, to_addrs, cc, bcc, reply_to,
               body_text, body_html, date, flags, read, starred,
               thread_id, message_id_header, in_reply_to, has_attachments, preview, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
              uid=excluded.uid, folder=excluded.folder, flags=excluded.flags,
              read=excluded.read, starred=excluded.starred, synced_at=excluded.synced_at,
              has_attachments=excluded.has_attachments, preview=excluded.preview
        """, (
            mid,
            data.get("uid", 0),
            data.get("folder", "INBOX"),
            data.get("subject", ""),
            data.get("from_addr", ""),
            data.get("to_addrs", ""),
            data.get("cc", ""),
            data.get("bcc", ""),
            data.get("reply_to", ""),
            data.get("body_text", ""),
            data.get("body_html", ""),
            data.get("date", ""),
            data.get("flags", ""),
            int(data.get("read", False)),
            int(data.get("starred", False)),
            data.get("thread_id", mid_header or mid),
            mid_header,
            data.get("in_reply_to", ""),
            int(data.get("has_attachments", False)),
            preview,
            now
        ))
        conn.commit()
        return get_message(mid) or {}
    finally:
        conn.close()


def get_message(message_id: str) -> dict | None:
    """Fetch a message by ID, including its attachments."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if not row:
            return None
        msg = _row_to_dict(row)
        msg["read"] = bool(msg["read"])
        msg["starred"] = bool(msg["starred"])
        msg["has_attachments"] = bool(msg["has_attachments"])
        msg["attachments"] = _get_attachments(conn, message_id)
        return msg
    finally:
        conn.close()


def list_folder(folder: str = "INBOX", limit: int = 100,
                unread_only: bool = False, starred_only: bool = False) -> list:
    """List messages in a folder, newest first."""
    conn = _get_conn()
    try:
        conditions = ["folder = ?"]
        params = [folder]
        if unread_only:
            conditions.append("read = 0")
        if starred_only:
            conditions.append("starred = 1")
        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM messages WHERE {where} ORDER BY date DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        result = []
        for row in rows:
            m = _row_to_dict(row)
            m["read"] = bool(m["read"])
            m["starred"] = bool(m["starred"])
            m["has_attachments"] = bool(m["has_attachments"])
            result.append(m)
        return result
    finally:
        conn.close()


def search_messages(query: str, folder: str = None, limit: int = 50) -> list:
    """Full-text search across subject, from, to, and body_text."""
    q = f"%{query}%"
    conn = _get_conn()
    try:
        if folder:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE folder = ? AND (subject LIKE ? OR from_addr LIKE ?
                         OR to_addrs LIKE ? OR body_text LIKE ? OR preview LIKE ?)
                   ORDER BY date DESC LIMIT ?""",
                (folder, q, q, q, q, q, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE subject LIKE ? OR from_addr LIKE ?
                         OR to_addrs LIKE ? OR body_text LIKE ? OR preview LIKE ?
                   ORDER BY date DESC LIMIT ?""",
                (q, q, q, q, q, limit)
            ).fetchall()
        result = []
        for row in rows:
            m = _row_to_dict(row)
            m["read"] = bool(m["read"])
            m["starred"] = bool(m["starred"])
            m["has_attachments"] = bool(m["has_attachments"])
            result.append(m)
        return result
    finally:
        conn.close()


def mark_read(message_id: str, read: bool = True) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE messages SET read = ? WHERE id = ?", (int(read), message_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def mark_starred(message_id: str, starred: bool = True) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE messages SET starred = ? WHERE id = ?", (int(starred), message_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def move_message(message_id: str, target_folder: str) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute(
            "UPDATE messages SET folder = ? WHERE id = ?", (target_folder, message_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_message(message_id: str) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_stats() -> dict:
    """Returns message counts per folder."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT folder, COUNT(*) as total, SUM(CASE WHEN read=0 THEN 1 ELSE 0 END) as unread "
            "FROM messages GROUP BY folder"
        ).fetchall()
        stats = {"inbox": 0, "inbox_unread": 0, "sent": 0, "drafts": 0, "trash": 0, "starred": 0}
        for row in rows:
            f = row["folder"].upper()
            if f == "INBOX":
                stats["inbox"] = row["total"]
                stats["inbox_unread"] = row["unread"] or 0
            elif f in ("SENT", "[GMAIL]/SENT", "SENT ITEMS"):
                stats["sent"] = row["total"]
            elif f == "TRASH":
                stats["trash"] = row["total"]
        # Starred is a flag, not a folder
        starred_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE starred = 1"
        ).fetchone()[0]
        stats["starred"] = starred_count
        # Drafts
        stats["drafts"] = conn.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]
        return stats
    finally:
        conn.close()


def get_uid_set(folder: str) -> set:
    """Returns the set of UIDs already in the DB for a folder (for efficient IMAP sync)."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT uid FROM messages WHERE folder = ? AND uid > 0", (folder,)
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()


# ── Attachment helpers ─────────────────────────────────────────────────────────

def _get_attachments(conn: sqlite3.Connection, message_id: str) -> list:
    rows = conn.execute(
        "SELECT * FROM attachments WHERE message_id = ?", (message_id,)
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def add_attachment(message_id: str, filename: str, size: int,
                   content_type: str, local_path: str) -> dict:
    aid = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO attachments (id, message_id, filename, size, content_type, local_path) "
            "VALUES (?,?,?,?,?,?)",
            (aid, message_id, filename, size, content_type, local_path)
        )
        conn.commit()
        return {"id": aid, "message_id": message_id, "filename": filename,
                "size": size, "content_type": content_type, "local_path": local_path}
    finally:
        conn.close()


# ── Drafts CRUD ────────────────────────────────────────────────────────────────

def save_draft(to_addrs: str = "", cc: str = "", bcc: str = "",
               subject: str = "", body: str = "", is_html: bool = False,
               draft_id: str = None) -> dict:
    """Create or update a draft. Returns the draft dict."""
    conn = _get_conn()
    try:
        now = datetime.utcnow().isoformat()
        if draft_id:
            conn.execute(
                """UPDATE drafts SET to_addrs=?, cc=?, bcc=?, subject=?, body=?, is_html=?, updated_at=?
                   WHERE id=?""",
                (to_addrs, cc, bcc, subject, body, int(is_html), now, draft_id)
            )
        else:
            draft_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO drafts (id, to_addrs, cc, bcc, subject, body, is_html, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (draft_id, to_addrs, cc, bcc, subject, body, int(is_html), now, now)
            )
        conn.commit()
        return get_draft(draft_id) or {}
    finally:
        conn.close()


def get_draft(draft_id: str) -> dict | None:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if row:
            d = _row_to_dict(row)
            d["is_html"] = bool(d["is_html"])
            return d
        return None
    finally:
        conn.close()


def list_drafts() -> list:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM drafts ORDER BY updated_at DESC").fetchall()
        result = []
        for row in rows:
            d = _row_to_dict(row)
            d["is_html"] = bool(d["is_html"])
            result.append(d)
        return result
    finally:
        conn.close()


def delete_draft(draft_id: str) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def clear_folder(folder: str) -> int:
    """Deletes all messages for a folder (used before full re-sync)."""
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM messages WHERE folder = ?", (folder,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
