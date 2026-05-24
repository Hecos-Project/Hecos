"""
MODULE: Contacts Store
DESCRIPTION: SQLite-based persistence layer for the Contacts plugin.
             DB: hecos/memory/contacts.db
             Two-table design: contacts (core data) + contact_fields (multi-value).
             Thread-safe via WAL mode.
"""

import sqlite3
import os
import uuid
import json
from datetime import datetime
from hecos.core.logging import logger


# ── Path resolution ────────────────────────────────────────────────────────────
def _get_db_path() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.normpath(os.path.join(_here, "..", ".."))  # hecos/
    mem_dir = os.path.join(_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return os.path.join(mem_dir, "contacts.db")


# ── Schema ─────────────────────────────────────────────────────────────────────
_CREATE_CONTACTS = """
CREATE TABLE IF NOT EXISTS contacts (
    id           TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    first_name   TEXT,
    last_name    TEXT,
    company      TEXT,
    role         TEXT,
    birthday     TEXT,
    address      TEXT,
    notes        TEXT,
    label_color  TEXT,
    tags         TEXT,
    photo_path   TEXT,
    photo_url    TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
"""

_CREATE_FIELDS = """
CREATE TABLE IF NOT EXISTS contact_fields (
    id         TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    field_type TEXT NOT NULL,
    label      TEXT,
    value      TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0
);
"""


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(_CREATE_CONTACTS)
    conn.execute(_CREATE_FIELDS)
    # Safe migration: add photo_url column if missing (for existing DBs)
    try:
        conn.execute("ALTER TABLE contacts ADD COLUMN photo_url TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    return conn


def _row_to_dict(row) -> dict:
    return dict(row)


# ── Contact CRUD ───────────────────────────────────────────────────────────────

def add(first_name: str, last_name: str = None, display_name: str = None,
        company: str = None, role: str = None, birthday: str = None,
        address: str = None, notes: str = None, label_color: str = None,
        tags: str = None, photo_path: str = None) -> dict:
    """Creates a new contact. Returns the contact dict with its new ID."""
    cid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    dn = display_name or f"{first_name} {last_name}".strip() if last_name else first_name
    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO contacts
               (id, display_name, first_name, last_name, company, role,
                birthday, address, notes, label_color, tags, photo_path, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid, dn, first_name, last_name, company, role,
             birthday, address, notes, label_color, tags, photo_path, now, now)
        )
        conn.commit()
        logger.debug("CONTACTS", f"Contact created: [{cid[:8]}] '{dn}'")
        return get_by_id(cid)
    finally:
        conn.close()


def get_by_id(contact_id: str) -> dict | None:
    """Fetch a contact by full UUID or 8-char prefix. Includes its multi-value fields."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM contacts WHERE id = ? OR SUBSTR(id,1,8) = ?",
            (contact_id, contact_id)
        ).fetchone()
        if not row:
            return None
        c = _row_to_dict(row)
        c["fields"] = _get_fields_for(conn, c["id"])
        return c
    finally:
        conn.close()


def search(query: str) -> list:
    """Search contacts by name, company, tag, or any field value."""
    q = f"%{query}%"
    conn = _get_conn()
    try:
        # Main fields search
        rows = conn.execute(
            """SELECT DISTINCT c.* FROM contacts c
               LEFT JOIN contact_fields f ON f.contact_id = c.id
               WHERE c.display_name LIKE ? OR c.first_name LIKE ? OR c.last_name LIKE ?
                  OR c.company LIKE ? OR c.tags LIKE ? OR f.value LIKE ?
               ORDER BY c.display_name ASC""",
            (q, q, q, q, q, q)
        ).fetchall()
        results = []
        for row in rows:
            c = _row_to_dict(row)
            c["fields"] = _get_fields_for(conn, c["id"])
            results.append(c)
        return results
    finally:
        conn.close()


def list_all(tag: str = None, limit: int = 100) -> list:
    """List all contacts, optionally filtered by tag."""
    conn = _get_conn()
    try:
        if tag:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE tags LIKE ? ORDER BY display_name ASC LIMIT ?",
                (f"%{tag}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contacts ORDER BY display_name ASC LIMIT ?",
                (limit,)
            ).fetchall()
        results = []
        for row in rows:
            c = _row_to_dict(row)
            c["fields"] = _get_fields_for(conn, c["id"])
            results.append(c)
        return results
    finally:
        conn.close()


def update(contact_id: str, **kwargs) -> bool:
    """Update specific fields of a contact. Accepts partial updates."""
    allowed = {"display_name", "first_name", "last_name", "company", "role",
               "birthday", "address", "notes", "label_color", "tags",
               "photo_path", "photo_url"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return False
    fields["updated_at"] = datetime.utcnow().isoformat()
    conn = _get_conn()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [contact_id, contact_id]
        cur = conn.execute(
            f"UPDATE contacts SET {set_clause} WHERE id = ? OR SUBSTR(id,1,8) = ?",
            vals
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete(contact_id: str) -> bool:
    """Delete a contact and all its fields (CASCADE). Returns True if deleted."""
    conn = _get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM contacts WHERE id = ? OR SUBSTR(id,1,8) = ?",
            (contact_id, contact_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def find_by_name(name: str) -> dict | None:
    """Finds the first contact matching a display or full name."""
    results = search(name)
    return results[0] if results else None


# ── Multi-value Fields ─────────────────────────────────────────────────────────

def add_field(contact_id: str, field_type: str, value: str,
              label: str = None, is_primary: bool = False) -> dict:
    """Add a phone/email/social/etc. field to a contact."""
    fid = str(uuid.uuid4())
    conn = _get_conn()
    try:
        # If this is marked primary, demote existing primaries
        if is_primary:
            conn.execute(
                "UPDATE contact_fields SET is_primary=0 WHERE contact_id=? AND field_type=?",
                (contact_id, field_type)
            )
        conn.execute(
            "INSERT INTO contact_fields (id, contact_id, field_type, label, value, is_primary) VALUES (?,?,?,?,?,?)",
            (fid, contact_id, field_type, label or field_type, value, int(is_primary))
        )
        conn.commit()
        return {"id": fid, "contact_id": contact_id, "field_type": field_type,
                "label": label, "value": value, "is_primary": is_primary}
    finally:
        conn.close()


def remove_field(field_id: str) -> bool:
    """Remove a specific multi-value field by ID."""
    conn = _get_conn()
    try:
        cur = conn.execute("DELETE FROM contact_fields WHERE id = ?", (field_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _get_fields_for(conn: sqlite3.Connection, contact_id: str) -> list:
    """Internal helper to load all fields for a contact using an open connection."""
    rows = conn.execute(
        "SELECT * FROM contact_fields WHERE contact_id = ? ORDER BY field_type, is_primary DESC",
        (contact_id,)
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_primary_field(contact_id: str, field_type: str) -> str | None:
    """Return the primary value for a given field_type (e.g. 'phone', 'whatsapp')."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM contact_fields WHERE contact_id=? AND field_type=? ORDER BY is_primary DESC LIMIT 1",
            (contact_id, field_type)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ── vCard export/import ────────────────────────────────────────────────────────

def export_vcard(contact_id: str) -> str:
    """Export a contact as a vCard 3.0 string."""
    c = get_by_id(contact_id)
    if not c:
        return ""
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"FN:{c.get('display_name', '')}",
        f"N:{c.get('last_name','')};{c.get('first_name','')};;;",
    ]
    if c.get("company"):
        lines.append(f"ORG:{c['company']}")
    if c.get("role"):
        lines.append(f"TITLE:{c['role']}")
    if c.get("birthday"):
        bday = c["birthday"].replace("-", "")[:8]
        lines.append(f"BDAY:{bday}")
    if c.get("address"):
        lines.append(f"ADR;TYPE=HOME:;;{c['address']};;;;")
    if c.get("notes"):
        lines.append(f"NOTE:{c['notes']}")
    for f in c.get("fields", []):
        ft = f["field_type"]
        v  = f["value"]
        lbl = (f.get("label") or ft).upper()
        if ft == "phone":
            lines.append(f"TEL;TYPE={lbl}:{v}")
        elif ft == "email":
            lines.append(f"EMAIL;TYPE={lbl}:{v}")
        elif ft in ("whatsapp", "telegram", "instagram", "linkedin", "twitter", "custom"):
            lines.append(f"X-{ft.upper()}:{v}")
    lines.append("END:VCARD")
    return "\r\n".join(lines)


def import_vcard(vcard_text: str) -> list:
    """Import one or more vCards from a .vcf string. Returns list of created contact dicts."""
    created = []
    current = {}
    multi_phones = []
    multi_emails = []
    for line in vcard_text.splitlines():
        line = line.strip()
        if line == "BEGIN:VCARD":
            current = {}
            multi_phones = []
            multi_emails = []
        elif line == "END:VCARD" and current:
            fn = current.get("first_name", "Unknown")
            ln = current.get("last_name")
            c = add(first_name=fn, last_name=ln, display_name=current.get("display_name"),
                    company=current.get("company"), role=current.get("role"),
                    birthday=current.get("birthday"), notes=current.get("notes"))
            for ph in multi_phones:
                add_field(c["id"], "phone", ph["value"], label=ph.get("label", "mobile"))
            for em in multi_emails:
                add_field(c["id"], "email", em["value"], label=em.get("label", "personal"))
            created.append(c)
        elif line.startswith("FN:"):
            current["display_name"] = line[3:]
        elif line.startswith("N:"):
            parts = line[2:].split(";")
            current["last_name"]  = parts[0] if len(parts) > 0 else ""
            current["first_name"] = parts[1] if len(parts) > 1 else ""
        elif line.startswith("ORG:"):
            current["company"] = line[4:]
        elif line.startswith("TITLE:"):
            current["role"] = line[6:]
        elif line.startswith("BDAY:"):
            raw = line[5:]
            if len(raw) == 8:
                current["birthday"] = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
        elif line.startswith("NOTE:"):
            current["notes"] = line[5:]
        elif "TEL" in line and ":" in line:
            label = "mobile"
            if "TYPE=" in line:
                label = line.split("TYPE=")[1].split(":")[0].split(";")[0].lower()
            value = line.split(":")[-1]
            multi_phones.append({"value": value, "label": label})
        elif "EMAIL" in line and ":" in line:
            label = "personal"
            if "TYPE=" in line:
                label = line.split("TYPE=")[1].split(":")[0].split(";")[0].lower()
            value = line.split(":")[-1]
            multi_emails.append({"value": value, "label": label})
    return created


# ── Birthday helpers ───────────────────────────────────────────────────────────

def get_birthdays_today() -> list:
    """Returns contacts whose birthday is today (MM-DD match)."""
    today = datetime.utcnow().strftime("%m-%d")
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE birthday LIKE ?",
            (f"%-{today}",)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_birthdays_upcoming(days: int = 7) -> list:
    """Returns contacts with a birthday in the next N days."""
    from datetime import timedelta
    now = datetime.utcnow()
    results = []
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM contacts WHERE birthday IS NOT NULL").fetchall()
        for row in rows:
            c = _row_to_dict(row)
            try:
                bd = c["birthday"][-5:]  # MM-DD
                this_year = datetime(now.year, int(bd[:2]), int(bd[3:]))
                if this_year < now:
                    this_year = datetime(now.year + 1, int(bd[:2]), int(bd[3:]))
                if (this_year - now).days <= days:
                    c["days_until_birthday"] = (this_year - now).days
                    results.append(c)
            except Exception:
                pass
        return sorted(results, key=lambda x: x["days_until_birthday"])
    finally:
        conn.close()
