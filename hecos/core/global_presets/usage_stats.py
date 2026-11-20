"""
hecos/core/global_presets/usage_stats.py
Persistent, lightweight usage statistics (distinct chat sessions, message count &
last-used timestamp) for Global Presets.
Automatically seeds historical counts once from `memory/users/*/history.db`
so existing presets immediately display accurate usage without mutating YAML files.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from hecos.core.constants import CONFIG_DATA_DIR, HECOS_DIR, MEMORY_DIR
from hecos.core.logging import logger

_USAGE_LOCK = threading.Lock()
_MAX_TRACKED_SESSIONS = 2000


def _default_usage_store_path() -> str:
    data_dir = os.path.join(HECOS_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "global_presets_usage.json")


def _normalize_iso_timestamp(raw_ts: str) -> str:
    clean = str(raw_ts or "").strip()
    if not clean:
        return ""
    if " " in clean and "T" not in clean:
        clean = clean.replace(" ", "T", 1)
    return clean


def _normalize_session_id(session_id: Optional[str]) -> str:
    sid = str(session_id or "").strip()
    if not sid or sid == "global":
        return ""
    return sid


def _public_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    msg_count = max(0, int(entry.get("message_count", entry.get("use_count", 0)) or 0))
    sessions = entry.get("sessions") if isinstance(entry.get("sessions"), list) else []
    chat_count = max(0, int(entry.get("chat_count") or 0), len(sessions))
    return {
        "chat_count": chat_count,
        "message_count": msg_count,
        "use_count": msg_count,
        "last_used_at": str(entry.get("last_used_at") or ""),
    }


def _seed_from_history_dbs(memory_dir: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Bootstrap preset chat/message counts and last-used dates from chat history SQLite DBs."""
    mem_root = memory_dir or MEMORY_DIR
    seeded: Dict[str, Dict[str, Any]] = {}
    if not mem_root or not os.path.isdir(mem_root):
        return seeded

    pattern = os.path.join(mem_root, "users", "*", "history.db")
    for db_path in glob.glob(pattern):
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            try:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(history)").fetchall()}
                if "model_info" not in cols or "timestamp" not in cols:
                    continue
                has_session_col = "session_id" in cols
                sql = (
                    "SELECT session_id, timestamp, model_info FROM history "
                    "WHERE role = 'assistant' AND model_info IS NOT NULL"
                    if has_session_col
                    else "SELECT '' AS session_id, timestamp, model_info FROM history "
                    "WHERE role = 'assistant' AND model_info IS NOT NULL"
                )
                cur = conn.execute(sql)
                for raw_sid, raw_ts, raw_info in cur:
                    if not raw_info:
                        continue
                    try:
                        info = json.loads(raw_info)
                    except Exception:
                        continue
                    if not isinstance(info, dict):
                        continue
                    pid = str(info.get("session_preset") or info.get("global_preset") or "").strip()
                    if not pid:
                        continue
                    iso_ts = _normalize_iso_timestamp(raw_ts)
                    sid = _normalize_session_id(raw_sid)
                    entry = seeded.setdefault(
                        pid,
                        {
                            "chat_count": 0,
                            "message_count": 0,
                            "use_count": 0,
                            "sessions": [],
                            "last_used_at": "",
                        },
                    )
                    entry["message_count"] = int(entry.get("message_count", 0)) + 1
                    entry["use_count"] = entry["message_count"]
                    if sid and sid not in entry["sessions"]:
                        entry["sessions"].append(sid)
                        entry["chat_count"] = len(entry["sessions"])
                    if iso_ts and iso_ts > str(entry.get("last_used_at", "")):
                        entry["last_used_at"] = iso_ts
            finally:
                conn.close()
        except Exception as exc:
            logger.debug(f"[GlobalPresets] History usage seed skipped for {db_path}: {exc}")

    for entry in seeded.values():
        sessions: List[str] = entry.get("sessions") or []
        entry["chat_count"] = max(int(entry.get("chat_count") or 0), len(sessions))
        if len(sessions) > _MAX_TRACKED_SESSIONS:
            entry["sessions"] = sessions[-_MAX_TRACKED_SESSIONS:]

    return seeded


def _load_usage_map_locked(store_path: str, memory_dir: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    if not os.path.isfile(store_path):
        seeded = _seed_from_history_dbs(memory_dir=memory_dir)
        _save_usage_map_locked(seeded, store_path)
        return seeded
    try:
        with open(store_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return {}

        needs_v2_migration = any(
            isinstance(v, dict) and ("chat_count" not in v or "message_count" not in v)
            for v in raw.values()
        )
        if needs_v2_migration:
            seeded = _seed_from_history_dbs(memory_dir=memory_dir)
            merged: Dict[str, Dict[str, Any]] = dict(seeded)
            # Preserve any preset whose history was previously deleted/archived
            for k, v in raw.items():
                pid = str(k)
                if pid in merged or not isinstance(v, dict):
                    continue
                old_cnt = max(0, int(v.get("use_count") or 0))
                merged[pid] = {
                    "chat_count": 1 if old_cnt > 0 else 0,
                    "message_count": old_cnt,
                    "use_count": old_cnt,
                    "sessions": [],
                    "last_used_at": _normalize_iso_timestamp(str(v.get("last_used_at") or "")),
                }
            _save_usage_map_locked(merged, store_path)
            return merged

        clean: Dict[str, Dict[str, Any]] = {}
        for k, v in raw.items():
            if not isinstance(v, dict):
                continue
            sessions = [
                _normalize_session_id(s)
                for s in (v.get("sessions") if isinstance(v.get("sessions"), list) else [])
                if _normalize_session_id(s)
            ]
            # Deduplicate preserving order
            dedup_sessions = list(dict.fromkeys(sessions))
            msg_count = max(0, int(v.get("message_count", v.get("use_count", 0)) or 0))
            chat_count = max(0, int(v.get("chat_count") or 0), len(dedup_sessions))
            clean[str(k)] = {
                "chat_count": chat_count,
                "message_count": msg_count,
                "use_count": msg_count,
                "sessions": dedup_sessions[-_MAX_TRACKED_SESSIONS:],
                "last_used_at": _normalize_iso_timestamp(str(v.get("last_used_at") or "")),
            }
        return clean
    except Exception:
        return {}


def _save_usage_map_locked(data: Dict[str, Dict[str, Any]], store_path: str) -> None:
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    tmp = f"{store_path}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, store_path)
    except OSError as exc:
        logger.debug(f"[GlobalPresets] Failed saving preset usage stats: {exc}")


def get_all_preset_usage(store_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Return `{soul_id: {"chat_count", "message_count", "use_count", "last_used_at"}}`."""
    path = store_path or _default_usage_store_path()
    with _USAGE_LOCK:
        data = _load_usage_map_locked(path)
        return {k: _public_entry(v) for k, v in data.items()}


def get_preset_usage(soul_id: str, store_path: Optional[str] = None) -> Dict[str, Any]:
    """Return usage metrics for a single Global Preset ID."""
    clean_id = str(soul_id or "").strip()
    if not clean_id:
        return {"chat_count": 0, "message_count": 0, "use_count": 0, "last_used_at": ""}
    all_usage = get_all_preset_usage(store_path=store_path)
    return dict(
        all_usage.get(clean_id)
        or {"chat_count": 0, "message_count": 0, "use_count": 0, "last_used_at": ""}
    )


def record_preset_usage(
    soul_id: str,
    *,
    session_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    store_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a completed assistant message for `soul_id`, tracking distinct chat sessions."""
    clean_id = str(soul_id or "").strip()
    if not clean_id:
        return {"chat_count": 0, "message_count": 0, "use_count": 0, "last_used_at": ""}

    path = store_path or _default_usage_store_path()
    now_iso = _normalize_iso_timestamp(timestamp) if timestamp else datetime.now().isoformat(timespec="seconds")
    norm_sid = _normalize_session_id(session_id)

    with _USAGE_LOCK:
        data = _load_usage_map_locked(path)
        cur = data.get(clean_id) or {
            "chat_count": 0,
            "message_count": 0,
            "use_count": 0,
            "sessions": [],
            "last_used_at": "",
        }
        prev_ts = str(cur.get("last_used_at") or "")
        sessions: List[str] = list(cur.get("sessions") or [])
        chat_count = max(0, int(cur.get("chat_count") or 0), len(sessions))
        msg_count = max(0, int(cur.get("message_count", cur.get("use_count", 0)) or 0)) + 1

        if norm_sid:
            if norm_sid not in sessions:
                sessions.append(norm_sid)
                chat_count = max(chat_count + 1, len(sessions))
                if len(sessions) > _MAX_TRACKED_SESSIONS:
                    sessions = sessions[-_MAX_TRACKED_SESSIONS:]
        elif chat_count == 0:
            chat_count = 1

        updated = {
            "chat_count": chat_count,
            "message_count": msg_count,
            "use_count": msg_count,
            "sessions": sessions,
            "last_used_at": now_iso if now_iso >= prev_ts else prev_ts,
        }
        data[clean_id] = updated
        _save_usage_map_locked(data, path)
        return _public_entry(updated)


def rebuild_preset_usage_from_history(
    *,
    store_path: Optional[str] = None,
    memory_dir: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Recalculate all preset usage stats directly from persisted chat history DBs."""
    path = store_path or _default_usage_store_path()
    with _USAGE_LOCK:
        seeded = _seed_from_history_dbs(memory_dir=memory_dir)
        _save_usage_map_locked(seeded, path)
        return {k: _public_entry(v) for k, v in seeded.items()}


def delete_preset_usage(soul_id: str, store_path: Optional[str] = None) -> None:
    """Remove persisted usage statistics when a Global Preset is deleted."""
    clean_id = str(soul_id or "").strip()
    if not clean_id:
        return
    path = store_path or _default_usage_store_path()
    with _USAGE_LOCK:
        data = _load_usage_map_locked(path)
        if clean_id in data:
            data.pop(clean_id, None)
            _save_usage_map_locked(data, path)


def resolve_soul_created_at(soul_id: str, raw_created_at: str = "", presets_dir: Optional[str] = None) -> str:
    """Return `created_at` from metadata or fall back to the preset YAML file timestamp on disk."""
    clean = _normalize_iso_timestamp(raw_created_at)
    if clean:
        return clean
    base_dir = presets_dir or os.path.join(CONFIG_DATA_DIR, "global_presets")
    filepath = os.path.join(base_dir, f"{soul_id}.global_preset.yaml")
    if os.path.isfile(filepath):
        try:
            st = os.stat(filepath)
            ts = min(st.st_ctime, st.st_mtime)
            return datetime.fromtimestamp(ts).isoformat(timespec="seconds")
        except OSError:
            pass
    return ""
