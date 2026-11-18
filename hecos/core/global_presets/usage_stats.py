"""
hecos/core/global_presets/usage_stats.py
Persistent, lightweight usage statistics (use count & last-used timestamp) for Global Presets.
Automatically seeds historical assistant turn counts once from `memory/users/*/history.db`
so existing presets immediately display accurate historical usage without mutating YAML files.
"""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from hecos.core.constants import CONFIG_DATA_DIR, HECOS_DIR, MEMORY_DIR
from hecos.core.logging import logger

_USAGE_LOCK = threading.Lock()


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


def _seed_from_history_dbs(memory_dir: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Bootstrap initial preset counts and last-used dates from existing chat history SQLite DBs."""
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
                cur = conn.execute(
                    "SELECT timestamp, model_info FROM history "
                    "WHERE role = 'assistant' AND model_info IS NOT NULL"
                )
                for raw_ts, raw_info in cur:
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
                    entry = seeded.setdefault(pid, {"use_count": 0, "last_used_at": ""})
                    entry["use_count"] = int(entry.get("use_count", 0)) + 1
                    if iso_ts and iso_ts > str(entry.get("last_used_at", "")):
                        entry["last_used_at"] = iso_ts
            finally:
                conn.close()
        except Exception as exc:
            logger.debug(f"[GlobalPresets] History usage seed skipped for {db_path}: {exc}")

    return seeded


def _load_usage_map_locked(store_path: str) -> Dict[str, Dict[str, Any]]:
    if not os.path.isfile(store_path):
        seeded = _seed_from_history_dbs()
        _save_usage_map_locked(seeded, store_path)
        return seeded
    try:
        with open(store_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return {}
        clean: Dict[str, Dict[str, Any]] = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                clean[str(k)] = {
                    "use_count": max(0, int(v.get("use_count") or 0)),
                    "last_used_at": str(v.get("last_used_at") or ""),
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
    """Return `{soul_id: {"use_count": int, "last_used_at": str}}` for all tracked presets."""
    path = store_path or _default_usage_store_path()
    with _USAGE_LOCK:
        data = _load_usage_map_locked(path)
        return {k: dict(v) for k, v in data.items()}


def get_preset_usage(soul_id: str, store_path: Optional[str] = None) -> Dict[str, Any]:
    """Return usage metrics for a single Global Preset ID."""
    clean_id = str(soul_id or "").strip()
    if not clean_id:
        return {"use_count": 0, "last_used_at": ""}
    all_usage = get_all_preset_usage(store_path=store_path)
    return dict(all_usage.get(clean_id) or {"use_count": 0, "last_used_at": ""})


def record_preset_usage(
    soul_id: str,
    *,
    timestamp: Optional[str] = None,
    store_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Increment `use_count` and update `last_used_at` for `soul_id`."""
    clean_id = str(soul_id or "").strip()
    if not clean_id:
        return {"use_count": 0, "last_used_at": ""}

    path = store_path or _default_usage_store_path()
    now_iso = _normalize_iso_timestamp(timestamp) if timestamp else datetime.now().isoformat(timespec="seconds")

    with _USAGE_LOCK:
        data = _load_usage_map_locked(path)
        cur = data.get(clean_id) or {"use_count": 0, "last_used_at": ""}
        prev_ts = str(cur.get("last_used_at") or "")
        updated = {
            "use_count": max(0, int(cur.get("use_count") or 0)) + 1,
            "last_used_at": now_iso if now_iso >= prev_ts else prev_ts,
        }
        data[clean_id] = updated
        _save_usage_map_locked(data, path)
        return dict(updated)


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
