"""
hecos/core/action_plans/store.py
Thread-safe atomic JSON persistence for shared Hecos Action Plans.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

_PLAN_STORE_LOCK = threading.Lock()
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")


def resolve_plans_dir(base_dir: Optional[str] = None) -> str:
    """Return directory path where structured Action Plans are persisted."""
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
        return os.path.abspath(base_dir)
    here = os.path.dirname(os.path.abspath(__file__))
    hecos_pkg_root = os.path.abspath(os.path.join(here, "..", ".."))
    target = os.path.join(hecos_pkg_root, "data", "action_plans")
    os.makedirs(target, exist_ok=True)
    return target


def _plan_path(plan_id: str, base_dir: Optional[str] = None) -> str:
    root = resolve_plans_dir(base_dir)
    pid = str(plan_id or "").strip()
    if not pid or not _SAFE_ID_RE.match(pid) or ".." in pid:
        pid = "plan_" + hashlib.sha256(pid.encode("utf-8", "ignore")).hexdigest()[:24]
    return os.path.join(root, f"{pid}.json")


def save_plan(plan: Dict[str, Any], base_dir: Optional[str] = None) -> str:
    """Atomically write an Action Plan dict to disk."""
    pid = str(plan.get("plan_id") or "").strip()
    if not pid:
        raise ValueError("Cannot save Action Plan without a valid plan_id.")
    path = _plan_path(pid, base_dir=base_dir)
    payload = json.loads(json.dumps(plan, ensure_ascii=False, default=str))
    payload["updated_at"] = time.time()

    with _PLAN_STORE_LOCK:
        tmp_path = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    return path


def load_plan(plan_id: Optional[str], base_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load an Action Plan record by ID, or None if missing/corrupt."""
    if not plan_id:
        return None
    path = _plan_path(plan_id, base_dir=base_dir)
    if not os.path.isfile(path):
        return None
    with _PLAN_STORE_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:
            return None


def list_plans(
    *,
    scope: Optional[str] = None,
    status: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = 50,
    base_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return persisted Action Plans ordered from newest to oldest."""
    root = resolve_plans_dir(base_dir)
    items: List[Dict[str, Any]] = []
    with _PLAN_STORE_LOCK:
        try:
            names = [f for f in os.listdir(root) if f.endswith(".json") and ".tmp." not in f]
        except OSError:
            names = []
        for fname in names:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    rec = json.load(fh)
                if not isinstance(rec, dict):
                    continue
                if scope and str(rec.get("scope") or "").lower() != str(scope).lower():
                    continue
                if status and str(rec.get("status") or "").lower() != str(status).lower():
                    continue
                if source_id and str(rec.get("source_id") or "") != str(source_id):
                    continue
                items.append(rec)
            except Exception:
                continue

    items.sort(key=lambda r: float(r.get("updated_at") or r.get("created_at") or 0), reverse=True)
    return items[:max(1, int(limit))]


def find_latest_plan_for_source(
    source_id: Optional[str],
    *,
    scope: Optional[str] = None,
    statuses: Optional[Iterable[str]] = None,
    base_dir: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Return the most recent plan bound to `source_id` matching optional filters."""
    if not source_id:
        return None
    allowed = {str(s).lower() for s in statuses} if statuses else None
    for plan in list_plans(scope=scope, source_id=str(source_id), limit=20, base_dir=base_dir):
        if allowed is None or str(plan.get("status") or "").lower() in allowed:
            return plan
    return None


def delete_plan(plan_id: Optional[str], base_dir: Optional[str] = None) -> bool:
    """Delete a persisted Action Plan file if it exists."""
    if not plan_id:
        return False
    path = _plan_path(plan_id, base_dir=base_dir)
    with _PLAN_STORE_LOCK:
        if os.path.isfile(path):
            try:
                os.remove(path)
                return True
            except OSError:
                return False
    return False


def cleanup_expired_plans(retention_days: int, base_dir: Optional[str] = None) -> int:
    """Remove Action Plans older than `retention_days` (0 keeps all)."""
    if int(retention_days or 0) <= 0:
        return 0
    cutoff = time.time() - (int(retention_days) * 86400)
    root = resolve_plans_dir(base_dir)
    removed = 0
    with _PLAN_STORE_LOCK:
        try:
            names = [f for f in os.listdir(root) if f.endswith(".json") and ".tmp." not in f]
        except OSError:
            return 0
        for fname in names:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    rec = json.load(fh)
                ts = float((rec or {}).get("updated_at") or (rec or {}).get("created_at") or os.path.getmtime(fpath))
                if ts < cutoff:
                    os.remove(fpath)
                    removed += 1
            except Exception:
                continue
    return removed
