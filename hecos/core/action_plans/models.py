"""
hecos/core/action_plans/models.py
Canonical models and normalization helpers for shared Hecos Action Plans.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

PLAN_STATUSES = frozenset({
    "draft",
    "awaiting_approval",
    "running",
    "paused",
    "interrupted",
    "completed",
    "failed",
    "cancelled",
})

ACTIVE_PLAN_STATUSES = frozenset({"draft", "awaiting_approval", "running", "paused", "interrupted"})
STEP_STATUSES = frozenset({"pending", "running", "done", "skipped", "failed"})
PLAN_MODES = frozenset({"auto", "confirm", "manual", "off"})


def normalize_step_status(raw: Any) -> str:
    """Normalize arbitrary step status aliases into a valid STEP_STATUSES string."""
    val = str(raw or "pending").strip().lower()
    aliases = {
        "completed": "done",
        "ok": "done",
        "finished": "done",
        "in_progress": "running",
        "active": "running",
        "working": "running",
        "error": "failed",
        "blocked": "failed",
        "todo": "pending",
        "waiting": "pending",
    }
    norm = aliases.get(val, val)
    return norm if norm in STEP_STATUSES else "pending"


def normalize_steps(raw_steps: Any) -> List[Dict[str, Any]]:
    """Coerce list[str|dict] or JSON/newline string into structured numbered step dicts."""
    items: List[Any] = []
    if isinstance(raw_steps, list):
        items = raw_steps
    elif isinstance(raw_steps, str):
        stripped = raw_steps.strip()
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    items = parsed
            except Exception:
                pass
        if not items and stripped:
            items = [
                line.lstrip("-*• ").strip()
                for line in stripped.splitlines()
                if line.lstrip("-*• ").strip()
            ]
    elif raw_steps is not None:
        items = [str(raw_steps)]

    normalized: List[Dict[str, Any]] = []
    for idx, entry in enumerate(items, start=1):
        if isinstance(entry, dict):
            title = str(entry.get("title") or entry.get("label") or entry.get("step") or f"Step {idx}").strip()
            status = normalize_step_status(entry.get("status"))
            notes = str(entry.get("notes") or "")
            step_id = str(entry.get("id") or f"step_{idx}")
            output_preview = str(entry.get("output_preview") or "")
        else:
            title = str(entry).strip()
            if not title:
                continue
            status = "pending"
            notes = ""
            step_id = f"step_{idx}"
            output_preview = ""

        normalized.append({
            "index": len(normalized) + 1,
            "id": step_id,
            "title": title[:260],
            "status": status,
            "notes": notes[:500],
            "output_preview": output_preview[:500],
            "updated_at": time.time(),
        })

    return normalized


def compute_plan_progress(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Return completion statistics and next actionable step for a plan dict."""
    steps = plan.get("steps") or []
    total = len(steps)
    done = sum(1 for s in steps if s.get("status") in ("done", "skipped"))
    failed = sum(1 for s in steps if s.get("status") == "failed")
    running = [s for s in steps if s.get("status") == "running"]
    pending = [s for s in steps if s.get("status") == "pending"]

    percent = int(round((done / total) * 100)) if total > 0 else 0
    next_step = running[0] if running else (pending[0] if pending else None)

    return {
        "total": total,
        "done": done,
        "failed": failed,
        "percent": percent,
        "next_step": next_step,
    }


def resolve_step_index(plan: Dict[str, Any], step_ref: Any) -> Optional[int]:
    """Resolve 1-based step index from integer index or string id/title prefix."""
    steps = plan.get("steps") or []
    if not steps:
        return None
    if isinstance(step_ref, int):
        return (step_ref - 1) if 1 <= step_ref <= len(steps) else None
    raw = str(step_ref or "").strip()
    if raw.isdigit():
        idx = int(raw)
        return (idx - 1) if 1 <= idx <= len(steps) else None
    low = raw.lower()
    for pos, st in enumerate(steps):
        if str(st.get("id") or "").lower() == low or str(st.get("title") or "").lower() == low:
            return pos
    return None


def new_plan_dict(
    *,
    title: str,
    steps: Any,
    scope: str = "agent",
    source_id: str = "",
    plan_mode: str = "auto",
    status: str = "running",
    metadata: Optional[Dict[str, Any]] = None,
    plan_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a canonical Action Plan record ready for persistence."""
    now = time.time()
    norm_steps = normalize_steps(steps)
    pid = (plan_id or f"plan_{uuid.uuid4().hex[:12]}").strip()
    return {
        "version": 1,
        "plan_id": pid,
        "title": (str(title or "Execution Plan").strip() or "Execution Plan")[:220],
        "scope": str(scope or "agent").strip().lower(),
        "source_id": str(source_id or "").strip(),
        "plan_mode": plan_mode if plan_mode in PLAN_MODES else "auto",
        "status": status if status in PLAN_STATUSES else "running",
        "summary": "",
        "steps": norm_steps,
        "metadata": dict(metadata or {}),
        "created_at": now,
        "updated_at": now,
    }
