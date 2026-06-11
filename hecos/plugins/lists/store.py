"""
MODULE: Lists Store
DESCRIPTION: SQLite-based persistence layer for lists, items and categories.
             DB: memory/lists.db
             All operations are thread-safe via SQLite WAL mode.
"""

import sqlite3
import os
import uuid
from datetime import datetime
from hecos.core.logging import logger

def _get_db_path() -> str:
    _here = os.path.dirname(os.path.abspath(__file__))
    _root = os.path.normpath(os.path.join(_here, "..", "..", "..")) # back to hecos/
    mem_dir = os.path.join(_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    return os.path.join(mem_dir, "lists.db")

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS lists (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    icon        TEXT,
    color       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    archived    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS list_items (
    id          TEXT PRIMARY KEY,
    list_id     TEXT NOT NULL,
    text        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    priority    INTEGER NOT NULL DEFAULT 0,
    label       TEXT,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(list_id) REFERENCES lists(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS list_categories (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    color       TEXT
);
"""

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(_CREATE_SQL)
    conn.commit()
    return conn

# ── Lists ──────────────────────────────────────────────────────────────────────

def create_list(name: str, icon: str = "📋", color: str = None) -> dict:
    lst = {
        "id": str(uuid.uuid4()),
        "name": name,
        "icon": icon,
        "color": color,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "archived": 0
    }
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO lists (id, name, icon, color, created_at, updated_at, archived) "
                "VALUES (:id, :name, :icon, :color, :created_at, :updated_at, :archived)",
                lst
            )
        return lst
    except Exception as e:
        logger.error(f"[LISTS] store.create_list error: {e}")
        return None

def get_lists(include_archived: bool = False) -> list:
    try:
        with _get_conn() as conn:
            if include_archived:
                rows = conn.execute("SELECT * FROM lists ORDER BY created_at DESC").fetchall()
            else:
                rows = conn.execute("SELECT * FROM lists WHERE archived = 0 ORDER BY created_at DESC").fetchall()
            
            # Count items
            lists = [dict(r) for r in rows]
            for lst in lists:
                count_row = conn.execute("SELECT COUNT(*) as c FROM list_items WHERE list_id = ? AND status = 'pending'", (lst['id'],)).fetchone()
                lst['pending_count'] = count_row['c'] if count_row else 0
        return lists
    except Exception as e:
        logger.error(f"[LISTS] store.get_lists error: {e}")
        return []

def get_list_by_id(list_id: str) -> dict | None:
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM lists WHERE id = ?", (list_id,)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        return None

def get_list_by_name(name: str) -> dict | None:
    try:
        with _get_conn() as conn:
            row = conn.execute("SELECT * FROM lists WHERE name LIKE ? AND archived = 0 LIMIT 1", (f"%{name}%",)).fetchone()
        return dict(row) if row else None
    except Exception as e:
        return None

def update_list(list_id: str, **kwargs) -> bool:
    allowed = {"name", "icon", "color", "archived"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields: return False
    
    fields["updated_at"] = datetime.now().isoformat()
    query = "UPDATE lists SET " + ", ".join(f"{k} = :{k}" for k in fields.keys()) + " WHERE id = :id"
    fields["id"] = list_id
    
    try:
        with _get_conn() as conn:
            conn.execute(query, fields)
        return True
    except Exception as e:
        logger.error(f"[LISTS] store.update_list error: {e}")
        return False

def delete_list(list_id: str) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
        return True
    except Exception as e:
        logger.error(f"[LISTS] store.delete_list error: {e}")
        return False

# ── List Items ─────────────────────────────────────────────────────────────────

def add_item(list_id: str, text: str, priority: int = 0, label: str = None) -> dict:
    item = {
        "id": str(uuid.uuid4()),
        "list_id": list_id,
        "text": text,
        "status": "pending",
        "priority": priority,
        "label": label,
        "position": 0,
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }
    try:
        with _get_conn() as conn:
            # get max position
            pos_row = conn.execute("SELECT MAX(position) as m FROM list_items WHERE list_id = ?", (list_id,)).fetchone()
            item["position"] = (pos_row["m"] or 0) + 1
            
            conn.execute(
                "INSERT INTO list_items (id, list_id, text, status, priority, label, position, created_at, completed_at) "
                "VALUES (:id, :list_id, :text, :status, :priority, :label, :position, :created_at, :completed_at)",
                item
            )
            # automatically save category if it's new
            if label:
                _save_category_if_new(conn, label)
                
            # update list updated_at
            conn.execute("UPDATE lists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), list_id))
        return item
    except Exception as e:
        logger.error(f"[LISTS] store.add_item error: {e}")
        return None

def get_items(list_id: str, status_filter: str = None) -> list:
    try:
        with _get_conn() as conn:
            if status_filter:
                rows = conn.execute("SELECT * FROM list_items WHERE list_id = ? AND status = ? ORDER BY position ASC, created_at ASC", (list_id, status_filter)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM list_items WHERE list_id = ? ORDER BY position ASC, created_at ASC", (list_id,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[LISTS] store.get_items error: {e}")
        return []

def update_item(item_id: str, **kwargs) -> bool:
    allowed = {"text", "status", "priority", "label", "position"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields: return False
    
    if "status" in fields and fields["status"] == "done":
        fields["completed_at"] = datetime.now().isoformat()
    elif "status" in fields:
        fields["completed_at"] = None
        
    all_fields = {**fields}
    query = "UPDATE list_items SET " + ", ".join(f"{k} = :{k}" for k in all_fields.keys()) + " WHERE id = :id"
    all_fields["id"] = item_id
    
    try:
        with _get_conn() as conn:
            conn.execute(query, all_fields)
            
            if "label" in fields and fields["label"]:
                _save_category_if_new(conn, fields["label"])
                
            # update parent list timestamp
            list_id_row = conn.execute("SELECT list_id FROM list_items WHERE id = ?", (item_id,)).fetchone()
            if list_id_row:
                conn.execute("UPDATE lists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), list_id_row["list_id"]))
                
        return True
    except Exception as e:
        logger.error(f"[LISTS] store.update_item error: {e}")
        return False

def delete_item(item_id: str) -> bool:
    try:
        with _get_conn() as conn:
            list_id_row = conn.execute("SELECT list_id FROM list_items WHERE id = ?", (item_id,)).fetchone()
            conn.execute("DELETE FROM list_items WHERE id = ?", (item_id,))
            if list_id_row:
                conn.execute("UPDATE lists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), list_id_row["list_id"]))
        return True
    except Exception as e:
        logger.error(f"[LISTS] store.delete_item error: {e}")
        return False

def clear_done_items(list_id: str) -> int:
    try:
        with _get_conn() as conn:
            cursor = conn.execute("DELETE FROM list_items WHERE list_id = ? AND status = 'done'", (list_id,))
            conn.execute("UPDATE lists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), list_id))
            return cursor.rowcount
    except Exception as e:
        logger.error(f"[LISTS] store.clear_done_items error: {e}")
        return 0

def reorder_items(list_id: str, ordered_ids: list) -> bool:
    try:
        with _get_conn() as conn:
            for idx, item_id in enumerate(ordered_ids):
                conn.execute("UPDATE list_items SET position = ? WHERE id = ? AND list_id = ?", (idx, item_id, list_id))
            conn.execute("UPDATE lists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), list_id))
        return True
    except Exception as e:
        logger.error(f"[LISTS] store.reorder_items error: {e}")
        return False

# ── Categories ─────────────────────────────────────────────────────────────────

def _save_category_if_new(conn: sqlite3.Connection, name: str):
    name = name.strip()
    if not name: return
    try:
        conn.execute("INSERT OR IGNORE INTO list_categories (id, name) VALUES (?, ?)", (str(uuid.uuid4()), name))
    except Exception:
        pass

def get_categories() -> list:
    try:
        with _get_conn() as conn:
            rows = conn.execute("SELECT * FROM list_categories ORDER BY name ASC").fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

def delete_category(cat_id: str) -> bool:
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM list_categories WHERE id = ?", (cat_id,))
        return True
    except Exception:
        return False
