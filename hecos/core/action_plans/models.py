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
PLAN_MODES = frozenset({"auto", "confirm", "plan_only", "manual", "off"})


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


def _normalize_step_files(raw_files: Any) -> List[str]:
    """Coerce optional per-step file paths into a compact deduplicated list."""
    if not raw_files:
        return []
    items: List[str] = []
    if isinstance(raw_files, list):
        candidates = raw_files
    elif isinstance(raw_files, str):
        stripped = raw_files.strip()
        candidates = []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    candidates = parsed
            except Exception:
                candidates = []
        if not candidates:
            candidates = [part.strip() for part in stripped.replace(";", "\n").replace(",", "\n").splitlines()]
    else:
        candidates = [str(raw_files)]

    seen = set()
    for c in candidates:
        clean = str(c or "").strip().strip("`")
        if clean and clean not in seen:
            seen.add(clean)
            items.append(clean[:180])
            if len(items) >= 12:
                break
    return items


def normalize_steps(raw_steps: Any) -> List[Dict[str, Any]]:
    """Coerce list[str|dict] or JSON/Python/newline string into structured numbered step dicts."""
    import ast
    import re

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
            if not items:
                try:
                    parsed = ast.literal_eval(stripped)
                    if isinstance(parsed, list):
                        items = parsed
                except Exception:
                    pass
            # Recover valid step titles/details from truncated JSON array strings instead of turning "[" into a step
            if not items:
                recovered_titles = re.findall(r'"title"\s*:\s*"((?:[^"\\]|\\.)+)"', stripped)
                if not recovered_titles:
                    recovered_titles = re.findall(r"'title'\s*:\s*'((?:[^'\\]|\\.)+)'", stripped)
                if recovered_titles:
                    items = [{"title": t.replace('\\"', '"').replace("\\'", "'")} for t in recovered_titles]
        if not items and stripped:
            _junk = {"[", "]", "{", "}", "```", "```json", ","}
            items = [
                line.lstrip("-*• ").strip()
                for line in stripped.splitlines()
                if line.lstrip("-*• ").strip() and line.lstrip("-*• ").strip() not in _junk
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
            files = _normalize_step_files(entry.get("files"))
            details = str(entry.get("details") or entry.get("description") or "").strip()
        else:
            title = str(entry).strip()
            if not title:
                continue
            status = "pending"
            notes = ""
            step_id = f"step_{idx}"
            output_preview = ""
            files = []
            details = ""

        step_rec: Dict[str, Any] = {
            "index": len(normalized) + 1,
            "id": step_id,
            "title": title[:300],
            "status": status,
            "notes": notes[:800],
            "output_preview": output_preview[:500],
            "updated_at": time.time(),
        }
        if files:
            step_rec["files"] = files
        if details:
            step_rec["details"] = details[:1200]
        normalized.append(step_rec)

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
    goal: str = "",
    plan_markdown: str = "",
    verification_plan: str = "",
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
        "revision": 1,
        "revision_history": [],
        "goal": str(goal or "").strip()[:1500],
        "plan_markdown": str(plan_markdown or "").strip()[:24000],
        "verification_plan": str(verification_plan or "").strip()[:3000],
        "summary": "",
        "steps": norm_steps,
        "metadata": dict(metadata or {}),
        "created_at": now,
        "updated_at": now,
    }


def build_plan_markdown_document(plan: Dict[str, Any], *, include_step_checklist: bool = True) -> str:
    """
    Build a rich Antigravity-style Implementation Plan Markdown document from a plan record.
    Uses the model-authored `plan_markdown` blueprint when present, or synthesizes structured
    sections from `goal`, `steps` (with `files`/`details`), and `verification_plan`.
    """
    if not isinstance(plan, dict):
        return ""

    title = str(plan.get("title") or "Implementation Plan").strip()
    rev = int(plan.get("revision") or 1)
    rev_tag = f" · **v{rev}**" if rev > 1 else ""
    goal = str(plan.get("goal") or "").strip()
    blueprint = str(plan.get("plan_markdown") or "").strip()
    verif = str(plan.get("verification_plan") or "").strip()
    steps = plan.get("steps") or []

    parts: List[str] = []

    if blueprint:
        if not blueprint.lstrip().startswith("#"):
            parts.append(f"# {title}{rev_tag}")
        else:
            if rev > 1:
                lines = blueprint.splitlines()
                if f"v{rev}" not in lines[0]:
                    lines[0] = f"{lines[0].rstrip()} *(v{rev})*"
                blueprint = "\n".join(lines)
        if goal and goal.lower()[:40] not in blueprint.lower():
            parts.append(f"## Goal\n\n{goal}")
        parts.append(blueprint)
        if verif and "verification" not in blueprint.lower() and "verifica" not in blueprint.lower():
            parts.append(f"## Verification Plan\n\n{verif}")
    else:
        parts.append(f"# {title}{rev_tag}")
        if goal:
            parts.append(f"## Goal\n\n{goal}")
        if steps:
            step_blocks: List[str] = ["## Proposed Changes & Execution Steps"]
            for s in steps:
                idx = s.get("index")
                stitle = str(s.get("title") or "").strip()
                sfiles = s.get("files") or []
                sdetails = str(s.get("details") or "").strip()
                snotes = str(s.get("notes") or "").strip()
                line = f"### {idx}. {stitle}"
                sub: List[str] = [line]
                if sfiles:
                    badges = " ".join(f"`{f}`" for f in sfiles)
                    sub.append(f"- **Files:** {badges}")
                if sdetails:
                    sub.append(f"- **Details:** {sdetails}")
                if snotes:
                    sub.append(f"- **Notes:** *{snotes}*")
                step_blocks.append("\n".join(sub))
            parts.append("\n\n".join(step_blocks))
        if verif:
            parts.append(f"## Verification Plan\n\n{verif}")

    if include_step_checklist and steps and blueprint:
        # Append a compact synchronized Execution Checklist so the user sees the exact trackable steps
        icons = {"done": "[x]", "running": "[ ]", "failed": "[ ]", "skipped": "[x]", "pending": "[ ]"}
        cl_lines = ["## Execution Checklist"]
        for s in steps:
            mark = icons.get(str(s.get("status") or "pending").lower(), "[ ]")
            files_txt = ""
            if s.get("files"):
                files_txt = " — " + ", ".join(f"`{f}`" for f in s["files"][:4])
            note_txt = f" *({s['notes']})*" if s.get("notes") else ""
            cl_lines.append(f"- {mark} **Step {s.get('index')}:** {s.get('title')}{files_txt}{note_txt}")
        parts.append("\n".join(cl_lines))

    return "\n\n".join(p for p in parts if p.strip()).strip()
