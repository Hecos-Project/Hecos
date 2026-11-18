"""
hecos/core/action_plans/flow_checkpoints.py
Atomic step-by-step checkpoint persistence and recovery helpers for Hecos Flows.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Set

_FLOW_CKPT_LOCK = threading.Lock()
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")
RESUMABLE_FLOW_STATUSES = frozenset({"running", "interrupted"})


def resolve_flow_checkpoints_dir(base_dir: Optional[str] = None) -> str:
    """Return storage directory for resumable Hecos Flow run checkpoints."""
    if base_dir:
        os.makedirs(base_dir, exist_ok=True)
        return os.path.abspath(base_dir)
    here = os.path.dirname(os.path.abspath(__file__))
    hecos_root = os.path.abspath(os.path.join(here, "..", ".."))
    target = os.path.join(hecos_root, "data", "flow_checkpoints")
    os.makedirs(target, exist_ok=True)
    return target


def _flow_ckpt_path(run_id: str, base_dir: Optional[str] = None) -> str:
    root = resolve_flow_checkpoints_dir(base_dir)
    rid = str(run_id or "").strip()
    if not rid or not _SAFE_ID_RE.match(rid) or ".." in rid:
        rid = "run_" + hashlib.sha256(rid.encode("utf-8", "ignore")).hexdigest()[:24]
    return os.path.join(root, f"{rid}.json")


def sanitize_flow_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize flow execution variables safely while preserving branch state."""
    safe: Dict[str, Any] = {}
    for k, v in (context or {}).items():
        if k in ("_run_id", "_flow_id"):
            continue
        try:
            json.dumps(v)
            safe[k] = v
        except Exception:
            safe[k] = str(v)[:4000]
    return safe


def save_flow_checkpoint(
    *,
    run_id: str,
    flow_id: str,
    flow_name: str,
    completed: Set[str] | List[str],
    skipped_nodes: Set[str] | List[str],
    context: Dict[str, Any],
    total_steps: int,
    status: str = "running",
    error_msg: str = "",
    base_dir: Optional[str] = None,
) -> Optional[str]:
    """Atomically save progress of a running Hecos Flow after each completed wave."""
    if not run_id or not flow_id:
        return None
    path = _flow_ckpt_path(run_id, base_dir=base_dir)
    now = time.time()

    with _FLOW_CKPT_LOCK:
        created_at = now
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    prev = json.load(fh)
                    created_at = float(prev.get("created_at") or now)
            except Exception:
                pass

        payload: Dict[str, Any] = {
            "version": 1,
            "run_id": str(run_id),
            "flow_id": str(flow_id),
            "flow_name": str(flow_name or flow_id),
            "status": str(status or "running"),
            "error_msg": str(error_msg or "")[:300],
            "completed": sorted(list(set(completed or []))),
            "skipped_nodes": sorted(list(set(skipped_nodes or []))),
            "total_steps": int(total_steps or 0),
            "context": sanitize_flow_context(context),
            "created_at": created_at,
            "updated_at": now,
        }
        tmp_path = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    return path


def load_flow_checkpoint(run_id: str, base_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load a persisted flow run checkpoint by `run_id`."""
    if not run_id:
        return None
    path = _flow_ckpt_path(run_id, base_dir=base_dir)
    if not os.path.isfile(path):
        return None
    with _FLOW_CKPT_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else None
        except Exception:
            return None


def mark_flow_checkpoint_status(
    run_id: str,
    status: str,
    *,
    error_msg: str = "",
    base_dir: Optional[str] = None,
) -> bool:
    """Atomically update flow checkpoint status (`completed`, `interrupted`, `dismissed`)."""
    if not run_id:
        return False
    path = _flow_ckpt_path(run_id, base_dir=base_dir)
    if not os.path.isfile(path):
        return False
    with _FLOW_CKPT_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return False
            data["status"] = str(status)
            if error_msg:
                data["error_msg"] = str(error_msg)[:300]
            data["updated_at"] = time.time()
            tmp_path = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
            return True
        except Exception:
            return False


def list_flow_checkpoints(
    *,
    flow_id: Optional[str] = None,
    only_resumable: bool = False,
    limit: int = 50,
    base_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List saved Flow checkpoints sorted by newest first."""
    root = resolve_flow_checkpoints_dir(base_dir)
    out: List[Dict[str, Any]] = []
    with _FLOW_CKPT_LOCK:
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
                if flow_id and rec.get("flow_id") != flow_id:
                    continue
                st = str(rec.get("status") or "").lower()
                if only_resumable and st not in RESUMABLE_FLOW_STATUSES:
                    continue
                out.append(rec)
            except Exception:
                continue
    out.sort(key=lambda r: float(r.get("updated_at") or r.get("created_at") or 0), reverse=True)
    return out[:max(1, int(limit))]


def delete_flow_checkpoint(run_id: str, base_dir: Optional[str] = None) -> bool:
    """Remove a flow checkpoint file from disk."""
    if not run_id:
        return False
    path = _flow_ckpt_path(run_id, base_dir=base_dir)
    with _FLOW_CKPT_LOCK:
        if os.path.isfile(path):
            try:
                os.remove(path)
                return True
            except OSError:
                return False
    return False


def cleanup_expired_flow_checkpoints(retention_days: int, base_dir: Optional[str] = None) -> int:
    """Delete flow checkpoints older than `retention_days` (0 keeps all)."""
    if int(retention_days or 0) <= 0:
        return 0
    cutoff = time.time() - (int(retention_days) * 86400)
    root = resolve_flow_checkpoints_dir(base_dir)
    removed = 0
    with _FLOW_CKPT_LOCK:
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
