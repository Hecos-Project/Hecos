"""
hecos/core/agent/checkpointing/store.py
Atomic JSON persistence for AgentExecutor turn-by-turn checkpoints.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

_STORE_LOCK = threading.Lock()
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
RESUMABLE_STATUSES = frozenset({"running", "interrupted"})


def _resolve_checkpoint_dir(override_dir: Optional[str] = None) -> str:
    """Return directory path where per-session agent checkpoints are stored."""
    if override_dir:
        os.makedirs(override_dir, exist_ok=True)
        return os.path.abspath(override_dir)
    pkg_here = os.path.dirname(os.path.abspath(__file__))
    hecos_pkg_root = os.path.abspath(os.path.join(pkg_here, "..", "..", ".."))
    target = os.path.join(hecos_pkg_root, "data", "agent_checkpoints")
    os.makedirs(target, exist_ok=True)
    return target


def _checkpoint_path(session_id: str, checkpoint_dir: Optional[str] = None) -> str:
    """Resolve safe JSON file path for a session_id without risking path traversal."""
    base_dir = _resolve_checkpoint_dir(checkpoint_dir)
    sid = str(session_id or "").strip()
    if not sid or not _SAFE_ID_RE.match(sid) or ".." in sid:
        sid = "sid_" + hashlib.sha256(sid.encode("utf-8", "ignore")).hexdigest()[:24]
    return os.path.join(base_dir, f"{sid}.json")


def serialize_agent_context(agent_context: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize in-memory agent_context entries into plain JSON-serializable dicts."""
    safe_list: List[Dict[str, Any]] = []
    for msg in agent_context or []:
        if isinstance(msg, dict):
            safe_list.append(json.loads(json.dumps(msg, default=str)))
        elif hasattr(msg, "model_dump"):
            safe_list.append(json.loads(json.dumps(msg.model_dump(), default=str)))
        elif hasattr(msg, "dict"):
            safe_list.append(json.loads(json.dumps(msg.dict(), default=str)))
        else:
            safe_list.append({"role": "assistant", "content": str(msg)})
    return safe_list


def serialize_tool_results(tool_results: List[Dict[str, Any]], max_items: int = 40) -> List[Dict[str, Any]]:
    """Persist bounded JSON-safe tool result metadata (preserving disk verification tags/outputs)."""
    trimmed = (tool_results or [])[-max_items:]
    out: List[Dict[str, Any]] = []
    for item in trimmed:
        if not isinstance(item, dict):
            continue
        copy = dict(item)
        raw_out = str(copy.get("output") or "")
        if len(raw_out) > 2500:
            copy["output"] = raw_out[:2500] + "\n...[truncated in checkpoint]"
        out.append(json.loads(json.dumps(copy, default=str)))
    return out


def save_turn_checkpoint(
    *,
    session_id: Optional[str],
    user_text: str,
    user_id: str = "admin",
    iteration: int,
    max_iterations: int,
    agent_context: List[Dict[str, Any]],
    accumulated_tool_results: List[Dict[str, Any]],
    retries_state: Optional[Dict[str, int]] = None,
    status: str = "running",
    reason: str = "",
    model_label: str = "",
    plan_id: str = "",
    checkpoint_dir: Optional[str] = None,
) -> Optional[str]:
    """Atomically persist current AgentExecutor state for crash/timeout resume."""
    if not session_id or not str(user_text or "").strip():
        return None
    path = _checkpoint_path(session_id, checkpoint_dir=checkpoint_dir)
    now = time.time()

    with _STORE_LOCK:
        existing_created = now
        existing_plan_id = ""
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    prev = json.load(fh)
                    existing_created = float(prev.get("created_at") or now)
                    existing_plan_id = str(prev.get("plan_id") or "")
            except Exception:
                pass

        payload: Dict[str, Any] = {
            "version": 1,
            "session_id": str(session_id),
            "user_id": str(user_id or "admin"),
            "user_text": str(user_text),
            "iteration": int(iteration),
            "max_iterations": int(max_iterations),
            "status": str(status or "running"),
            "reason": str(reason or ""),
            "model_label": str(model_label or ""),
            "plan_id": str(plan_id or existing_plan_id or ""),
            "retries_state": dict(retries_state or {"stream": 0, "file": 0, "netsearch": 0}),
            "agent_context": serialize_agent_context(agent_context),
            "accumulated_tool_results": serialize_tool_results(accumulated_tool_results),
            "created_at": existing_created,
            "updated_at": now,
        }
        tmp_path = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    return path


def load_checkpoint(session_id: Optional[str], checkpoint_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load saved checkpoint dict for `session_id`, or None if missing/corrupt."""
    if not session_id:
        return None
    path = _checkpoint_path(session_id, checkpoint_dir=checkpoint_dir)
    if not os.path.isfile(path):
        return None
    with _STORE_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else None
        except Exception:
            return None


def mark_checkpoint_status(
    session_id: Optional[str],
    status: str,
    *,
    reason: str = "",
    final_preview: str = "",
    checkpoint_dir: Optional[str] = None,
) -> bool:
    """Update status/reason of an existing checkpoint atomically."""
    if not session_id:
        return False
    path = _checkpoint_path(session_id, checkpoint_dir=checkpoint_dir)
    if not os.path.isfile(path):
        return False
    with _STORE_LOCK:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return False
            data["status"] = str(status)
            if reason:
                data["reason"] = str(reason)[:300]
            if final_preview:
                data["final_preview"] = str(final_preview)[:300]
            data["updated_at"] = time.time()
            tmp_path = f"{path}.tmp.{os.getpid()}.{threading.get_ident()}"
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
            return True
        except Exception:
            return False


def delete_checkpoint(session_id: Optional[str], checkpoint_dir: Optional[str] = None) -> bool:
    """Remove a session checkpoint file if present."""
    if not session_id:
        return False
    path = _checkpoint_path(session_id, checkpoint_dir=checkpoint_dir)
    with _STORE_LOCK:
        if os.path.isfile(path):
            try:
                os.remove(path)
                return True
            except OSError:
                return False
    return False


def is_resumable_checkpoint(record: Optional[Dict[str, Any]]) -> bool:
    """Return True if a checkpoint represents an unfinished/interrupted runnable task."""
    if not isinstance(record, dict):
        return False
    if str(record.get("status") or "").lower() not in RESUMABLE_STATUSES:
        return False
    return bool(str(record.get("user_text") or "").strip())


def list_checkpoints(limit: int = 50, checkpoint_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """List persisted session checkpoints ordered from newest to oldest."""
    root = _resolve_checkpoint_dir(checkpoint_dir)
    out: List[Dict[str, Any]] = []
    with _STORE_LOCK:
        try:
            names = [f for f in os.listdir(root) if f.endswith(".json") and ".tmp." not in f]
        except OSError:
            names = []
        for fname in names:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as fh:
                    rec = json.load(fh)
                if isinstance(rec, dict):
                    out.append(rec)
            except Exception:
                continue
    out.sort(key=lambda r: float(r.get("updated_at") or r.get("created_at") or 0), reverse=True)
    return out[:max(1, int(limit))]


def cleanup_expired_checkpoints(retention_days: int, checkpoint_dir: Optional[str] = None) -> int:
    """Delete checkpoints older than `retention_days` (0 disables expiration)."""
    if int(retention_days or 0) <= 0:
        return 0
    cutoff = time.time() - (int(retention_days) * 86400)
    root = _resolve_checkpoint_dir(checkpoint_dir)
    removed = 0
    with _STORE_LOCK:
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
