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


def resolve_media_plans_dir(media_dir: Optional[str] = None) -> str:
    """Return centralized human-readable Action Plans directory under hecos/media/action_plans."""
    if media_dir:
        target = os.path.abspath(media_dir)
    else:
        from hecos.core.constants import PLANS_DIR
        target = os.path.abspath(PLANS_DIR)
    os.makedirs(target, exist_ok=True)
    return target


def _mirror_filename(plan: Dict[str, Any]) -> str:
    """Build deterministic human-readable Markdown filename `<slug>_<plan_id>.md`."""
    raw_title = str(plan.get("title") or "action_plan").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "_", raw_title).strip("_")[:48] or "action_plan"
    pid = str(plan.get("plan_id") or "").strip()
    if not pid or not _SAFE_ID_RE.match(pid) or ".." in pid:
        pid = "plan_" + hashlib.sha256(pid.encode("utf-8", "ignore")).hexdigest()[:16]
    return f"{slug}_{pid}.md"


def _remove_media_mirror_for_id(plan_id: str, target_dir: str, keep_basename: str = "") -> None:
    """Remove stale mirror files matching `plan_id` inside `target_dir`."""
    if not plan_id or not os.path.isdir(target_dir):
        return
    suffix = f"_{plan_id}.md"
    try:
        for fname in os.listdir(target_dir):
            if fname.endswith(suffix) and fname != keep_basename:
                fpath = os.path.join(target_dir, fname)
                if os.path.isfile(fpath):
                    os.remove(fpath)
    except OSError:
        pass


def sync_plan_media_mirror(plan: Dict[str, Any], media_dir: Optional[str] = None) -> Optional[str]:
    """Write or refresh the human-readable `.md` mirror of `plan` inside `hecos/media/action_plans`."""
    pid = str((plan or {}).get("plan_id") or "").strip()
    if not pid or not isinstance(plan, dict):
        return None
    try:
        from hecos.core.action_plans.io_codec import serialize_plan_for_export

        target_dir = resolve_media_plans_dir(media_dir)
        fname = _mirror_filename(plan)
        dest_path = os.path.join(target_dir, fname)
        md_content, _, _ = serialize_plan_for_export(plan, fmt="md")

        _remove_media_mirror_for_id(pid, target_dir, keep_basename=fname)
        tmp_path = f"{dest_path}.tmp.{os.getpid()}.{threading.get_ident()}"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(md_content)
        os.replace(tmp_path, dest_path)
        return dest_path
    except Exception:
        return None


def sync_all_plans_to_media_dir(base_dir: Optional[str] = None, media_dir: Optional[str] = None) -> int:
    """Ensure persisted Action Plans (skipping cancelled/corrupt placeholders) are mirrored in media/action_plans."""
    synced = 0
    for rec in list_plans(limit=100, base_dir=base_dir):
        if str(rec.get("status") or "").lower() == "cancelled":
            continue
        steps = rec.get("steps") or []
        if not steps or (len(steps) == 1 and str(steps[0].get("title") or "").strip() in ("[", "{", "")):
            continue
        if sync_plan_media_mirror(rec, media_dir=media_dir):
            synced += 1
    return synced


def _plan_path(plan_id: str, base_dir: Optional[str] = None) -> str:
    root = resolve_plans_dir(base_dir)
    pid = str(plan_id or "").strip()
    if not pid or not _SAFE_ID_RE.match(pid) or ".." in pid:
        pid = "plan_" + hashlib.sha256(pid.encode("utf-8", "ignore")).hexdigest()[:24]
    return os.path.join(root, f"{pid}.json")


def save_plan(
    plan: Dict[str, Any],
    base_dir: Optional[str] = None,
    *,
    mirror_to_media: Optional[bool] = None,
    media_dir: Optional[str] = None,
) -> str:
    """Atomically write an Action Plan dict to disk and auto-save a readable `.md` copy in media/action_plans."""
    pid = str(plan.get("plan_id") or "").strip()
    if not pid:
        raise ValueError("Cannot save Action Plan without a valid plan_id.")
    path = _plan_path(pid, base_dir=base_dir)
    payload = json.loads(json.dumps(plan, ensure_ascii=False, default=str))
    payload["updated_at"] = time.time()

    should_mirror = (base_dir is None) if mirror_to_media is None else bool(mirror_to_media)
    if should_mirror:
        # Don't clutter media/action_plans with trivial cancelled junk
        st_low = str(payload.get("status") or "").lower()
        steps = payload.get("steps") or []
        is_valid_plan = bool(steps) and not (len(steps) == 1 and str(steps[0].get("title") or "").strip() in ("[", "{", ""))
        if st_low != "cancelled" and is_valid_plan:
            mirror_path = sync_plan_media_mirror(payload, media_dir=media_dir)
            if mirror_path:
                payload["media_file"] = os.path.basename(mirror_path)
                payload["media_path"] = mirror_path

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


def delete_plan(plan_id: Optional[str], base_dir: Optional[str] = None, *, media_dir: Optional[str] = None) -> bool:
    """Delete a persisted Action Plan file (and its media mirror when removing production plans)."""
    if not plan_id:
        return False
    path = _plan_path(plan_id, base_dir=base_dir)
    removed = False
    with _PLAN_STORE_LOCK:
        if os.path.isfile(path):
            try:
                os.remove(path)
                removed = True
            except OSError:
                return False
        if base_dir is None or media_dir:
            try:
                _remove_media_mirror_for_id(str(plan_id), resolve_media_plans_dir(media_dir))
            except Exception:
                pass
    return removed


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
