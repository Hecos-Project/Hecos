"""
hecos/core/action_plans/manager.py
Shared Core orchestrator for creating, updating, approving, and summarizing Action Plans.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from hecos.core.action_plans.approval_gate import (
    await_plan_approval,
    has_pending_approval,
    submit_approval_decision,
)
from hecos.core.action_plans.config import get_action_plans_config
from hecos.core.action_plans.events import emit_plan_event
from hecos.core.action_plans.models import (
    ACTIVE_PLAN_STATUSES,
    PLAN_STATUSES,
    build_plan_markdown_document,
    compute_plan_progress,
    new_plan_dict,
    normalize_step_status,
    normalize_steps,
    resolve_step_index,
)
from hecos.core.action_plans.store import (
    delete_plan,
    find_latest_plan_for_source,
    list_plans,
    load_plan,
    save_plan,
)


def resolve_active_session_context() -> Dict[str, Any]:
    """Inspect active TraceSession (if any) without creating UI coupling."""
    try:
        from hecos.core.agent.trace_session import get_active_session
        sess = get_active_session()
        if sess is not None:
            t_cfg = getattr(sess, "config", None) or {}
            return {
                "session_id": str(sess.session_id or ""),
                "has_trace_callback": sess.trace_callback is not None,
                "state_manager": sess.state_manager,
                "turn_plan_only": bool(isinstance(t_cfg, dict) and t_cfg.get("_turn_plan_only")),
                "turn_revise_plan_id": str(t_cfg.get("_turn_revise_plan_id") or "").strip() if isinstance(t_cfg, dict) else "",
                "turn_config": t_cfg if isinstance(t_cfg, dict) else {},
            }
    except Exception:
        pass
    return {
        "session_id": "",
        "has_trace_callback": False,
        "state_manager": None,
        "turn_plan_only": False,
        "turn_revise_plan_id": "",
        "turn_config": {},
    }


class ActionPlanManager:
    """Shared lifecycle manager for multi-step Action Plans across Core, Flows, and Plugins."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir
        self._lock = threading.RLock()

    def create_plan(
        self,
        *,
        title: str,
        steps: Any,
        scope: str = "agent",
        source_id: str = "",
        goal: str = "",
        plan_markdown: str = "",
        verification_plan: str = "",
        require_approval: Optional[bool] = None,
        wait_for_approval: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and persist a structured Action Plan, optionally awaiting user confirmation."""
        cfg = get_action_plans_config()
        ctx = resolve_active_session_context()
        eff_source = str(source_id or ctx["session_id"] or "").strip()

        # If this turn explicitly targets an existing plan for revision and the LLM called
        # create_plan instead of revise_plan, evolve the existing plan in-place to preserve continuity.
        revise_target = str(ctx.get("turn_revise_plan_id") or "").strip()
        if revise_target and scope == "agent":
            existing_target = load_plan(revise_target, base_dir=self.base_dir)
            if existing_target and existing_target.get("status") not in ("completed", "cancelled"):
                return self.revise_plan(
                    plan_id=revise_target,
                    title=title,
                    goal=goal or None,
                    plan_markdown=plan_markdown or None,
                    steps=steps,
                    verification_plan=verification_plan or None,
                    revision_note=str((metadata or {}).get("revision_note") or "Revised in Architect Mode"),
                    source_id=eff_source,
                    keep_awaiting_approval=True,
                )

        meta_dict = dict(metadata or {})
        is_explicit_plan_only_turn = bool(
            meta_dict.get("plan_only")
            or (scope == "agent" and ctx.get("turn_plan_only"))
        )
        is_plan_only = bool(
            is_explicit_plan_only_turn
            or (
                require_approval is not False
                and scope == "agent"
                and str(cfg.get("plan_mode") or "").lower() == "plan_only"
            )
        )

        if is_plan_only:
            needs_approval = True
            wait_for_approval = False
            effective_plan_mode = "plan_only"
        else:
            if require_approval is None:
                needs_approval = (cfg.get("plan_mode") == "confirm")
            else:
                needs_approval = bool(require_approval)
            effective_plan_mode = cfg.get("plan_mode", "auto")

        initial_status = "awaiting_approval" if (needs_approval and wait_for_approval and ctx["has_trace_callback"]) else (
            "awaiting_approval" if (needs_approval and not wait_for_approval) else "running"
        )
        plan = new_plan_dict(
            title=title,
            steps=steps,
            scope=scope,
            source_id=eff_source,
            plan_mode=effective_plan_mode,
            status=initial_status,
            goal=goal,
            plan_markdown=plan_markdown,
            verification_plan=verification_plan,
            metadata=meta_dict,
        )

        # Auto-mark step 1 running when immediately executable
        if plan["status"] == "running" and plan["steps"] and plan["steps"][0]["status"] == "pending":
            plan["steps"][0]["status"] = "running"

        with self._lock:
            # Close out any stale active plan for the same source so only one active plan tracks UI
            if eff_source:
                prev = find_latest_plan_for_source(
                    eff_source, scope=scope, statuses=ACTIVE_PLAN_STATUSES, base_dir=self.base_dir
                )
                if prev and prev.get("plan_id") != plan["plan_id"]:
                    prev["status"] = "cancelled"
                    prev["summary"] = "Replaced by a newer plan."
                    save_plan(prev, base_dir=self.base_dir)
            save_plan(plan, base_dir=self.base_dir)

        if initial_status == "awaiting_approval" and wait_for_approval and ctx["has_trace_callback"]:
            sm = ctx["state_manager"]
            decision = await_plan_approval(
                plan,
                timeout_sec=float(cfg.get("approval_timeout_seconds", 300)),
                abort_checker=(lambda: bool(sm and getattr(sm, "webui_stop_requested", False))) if sm else None,
            )
            with self._lock:
                fresh = load_plan(plan["plan_id"], base_dir=self.base_dir) or plan
                if decision.get("approved"):
                    if decision.get("edited_steps"):
                        fresh["steps"] = normalize_steps(decision["edited_steps"])
                    fresh["status"] = "running"
                    if fresh["steps"] and fresh["steps"][0]["status"] == "pending":
                        fresh["steps"][0]["status"] = "running"
                    save_plan(fresh, base_dir=self.base_dir)
                    emit_plan_event("plan_approved", fresh)
                    return {"ok": True, "approved": True, "plan": fresh}
                else:
                    reason = str(decision.get("reason") or "rejected")
                    fresh["status"] = "cancelled"
                    fresh["summary"] = f"Cancelled ({reason})"
                    save_plan(fresh, base_dir=self.base_dir)
                    emit_plan_event("plan_rejected", fresh)
                    return {"ok": False, "approved": False, "reason": reason, "plan": fresh}

        emit_plan_event("plan_created" if plan["status"] == "running" else "approval_required", plan)
        return {
            "ok": True,
            "approved": True if is_plan_only else (plan["status"] == "running"),
            "plan_only": is_plan_only,
            "plan": plan,
        }

    def revise_plan(
        self,
        *,
        plan_id: str = "",
        title: Optional[str] = None,
        goal: Optional[str] = None,
        plan_markdown: Optional[str] = None,
        steps: Optional[Any] = None,
        verification_plan: Optional[str] = None,
        revision_note: str = "",
        source_id: str = "",
        keep_awaiting_approval: bool = True,
    ) -> Dict[str, Any]:
        """Revise an existing Action Plan's blueprint and/or steps, incrementing its revision counter."""
        ctx = resolve_active_session_context()
        eff_source = str(source_id or ctx["session_id"] or "").strip()
        target_id = str(plan_id or ctx.get("turn_revise_plan_id") or "").strip()

        with self._lock:
            plan = self.resolve_plan(plan_id=target_id, source_id=eff_source)
            if not plan or plan.get("status") in ("completed", "cancelled"):
                return self.create_plan(
                    title=str(title or "Execution Plan"),
                    steps=steps or ["Analyze requirements and implement requested changes"],
                    scope="agent",
                    source_id=eff_source,
                    goal=str(goal or ""),
                    plan_markdown=str(plan_markdown or ""),
                    verification_plan=str(verification_plan or ""),
                    require_approval=True,
                    wait_for_approval=False,
                    metadata={"plan_only": True},
                )

            if title is not None and str(title).strip():
                plan["title"] = str(title).strip()[:220]
            if goal is not None:
                plan["goal"] = str(goal).strip()[:1500]
            if plan_markdown is not None:
                plan["plan_markdown"] = str(plan_markdown).strip()[:24000]
            if verification_plan is not None:
                plan["verification_plan"] = str(verification_plan).strip()[:3000]
            if steps is not None:
                prev_done_titles = {
                    str(s.get("title") or "").strip().lower(): s
                    for s in (plan.get("steps") or [])
                    if s.get("status") in ("done", "skipped")
                }
                new_steps = normalize_steps(steps)
                if new_steps:
                    # Preserve already-verified steps if revising an interrupted/paused plan
                    if plan.get("status") in ("interrupted", "paused", "running"):
                        for st in new_steps:
                            prev = prev_done_titles.get(str(st.get("title") or "").strip().lower())
                            if prev:
                                st["status"] = prev.get("status", "done")
                                if not st.get("notes") and prev.get("notes"):
                                    st["notes"] = prev["notes"]
                    plan["steps"] = new_steps

            next_rev = int(plan.get("revision") or 1) + 1
            plan["revision"] = next_rev
            history = list(plan.get("revision_history") or [])
            history.append({
                "revision": next_rev,
                "note": str(revision_note or "Plan revised").strip()[:400],
                "timestamp": time.time(),
            })
            plan["revision_history"] = history[-15:]

            if keep_awaiting_approval and plan.get("status") not in ("completed", "cancelled"):
                plan["plan_mode"] = "plan_only"
                plan["status"] = "awaiting_approval"

            save_plan(plan, base_dir=self.base_dir)

        emit_plan_event("plan_revised", plan)
        return {
            "ok": True,
            "approved": True,
            "plan_only": True,
            "revised": True,
            "plan": plan,
        }

    def update_step(
        self,
        *,
        plan_id: str = "",
        step_ref: Any = 1,
        status: str = "done",
        notes: str = "",
        output_preview: str = "",
        source_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Update a plan step status and automatically advance the next pending step to `running`."""
        with self._lock:
            plan = self.resolve_plan(plan_id=plan_id, source_id=source_id)
            if not plan:
                return None

            idx = resolve_step_index(plan, step_ref)
            if idx is None:
                return None

            norm_status = normalize_step_status(status)
            step = plan["steps"][idx]
            step["status"] = norm_status
            if notes:
                step["notes"] = str(notes)[:500]
            if output_preview:
                step["output_preview"] = str(output_preview)[:500]
            step["updated_at"] = time.time()

            # Promote next pending step to running when finishing current one
            if norm_status in ("done", "skipped"):
                has_running = any(s.get("status") == "running" for s in plan["steps"])
                if not has_running:
                    for cand in plan["steps"][idx + 1:]:
                        if cand.get("status") == "pending":
                            cand["status"] = "running"
                            cand["updated_at"] = time.time()
                            break

            prog = compute_plan_progress(plan)
            if prog["total"] > 0 and prog["done"] >= prog["total"] and prog["failed"] == 0:
                plan["status"] = "completed"
            elif plan.get("status") in ("draft", "paused", "interrupted"):
                plan["status"] = "running"

            save_plan(plan, base_dir=self.base_dir)

        emit_plan_event("step_updated", plan)
        return plan

    def toggle_step_manual(
        self,
        *,
        plan_id: str,
        step_ref: Any,
        status: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Manually toggle or set a step's status (done <-> pending) without spinning up the next step."""
        with self._lock:
            plan = self.resolve_plan(plan_id=plan_id)
            if not plan:
                return {"ok": False, "error": f"Plan '{plan_id}' not found"}

            idx = resolve_step_index(plan, step_ref)
            if idx is None:
                return {"ok": False, "error": f"Step {step_ref} out of range"}

            step = plan["steps"][idx]
            cur_st = str(step.get("status") or "pending").lower()
            desired = normalize_step_status(status) if str(status or "").strip() else (
                "pending" if cur_st == "done" else "done"
            )
            step["status"] = desired
            if notes:
                step["notes"] = str(notes)[:500]
            step["updated_at"] = time.time()

            prog = compute_plan_progress(plan)
            if prog["total"] > 0 and prog["done"] >= prog["total"] and prog["failed"] == 0:
                plan["status"] = "completed"
            elif plan.get("status") == "completed" and prog["done"] < prog["total"]:
                plan["status"] = "awaiting_approval" if plan.get("plan_mode") == "plan_only" else "paused"

            plan["updated_at"] = time.time()
            save_plan(plan, base_dir=self.base_dir)

        emit_plan_event("step_updated", plan)
        return {"ok": True, "plan": plan}

    def complete_plan(
        self,
        *,
        plan_id: str = "",
        status: str = "completed",
        summary: str = "",
        source_id: str = "",
        allow_incomplete: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Finalize an Action Plan and emit completion notification.
        When `allow_incomplete=False` (used by LLM tools) and pending/failed steps still
        remain, refuses premature 'completed' transition so remaining steps aren't skipped.
        """
        target_status = str(status or "completed").strip().lower()
        if target_status not in PLAN_STATUSES:
            target_status = "completed"

        with self._lock:
            plan = self.resolve_plan(plan_id=plan_id, source_id=source_id)
            if not plan:
                return None
            if target_status == "completed":
                steps = plan.get("steps") or []
                if not allow_incomplete and steps:
                    pending_or_failed = [s for s in steps if s.get("status") in ("pending", "failed")]
                    running_steps = [s for s in steps if s.get("status") == "running"]
                    # Block premature completion whenever any step wasn't even started, or >1 running step remains
                    if pending_or_failed or len(running_steps) > 1:
                        plan["status"] = "running"
                        if not running_steps and pending_or_failed:
                            pending_or_failed[0]["status"] = "running"
                            pending_or_failed[0]["updated_at"] = time.time()
                        save_plan(plan, base_dir=self.base_dir)
                        emit_plan_event("step_updated", plan)
                        blocked = dict(plan)
                        blocked["_completion_blocked"] = True
                        blocked["_incomplete_steps"] = [
                            f"Step {s.get('index')}: {s.get('title')}"
                            for s in (running_steps + pending_or_failed)[:8]
                        ]
                        return blocked
                for st in steps:
                    if st.get("status") == "running":
                        st["status"] = "done"
                        st["updated_at"] = time.time()
            plan["status"] = target_status
            if summary:
                plan["summary"] = str(summary)[:500]
            save_plan(plan, base_dir=self.base_dir)

        emit_plan_event("plan_completed", plan)
        return plan

    def resolve_plan(self, *, plan_id: str = "", source_id: str = "") -> Optional[Dict[str, Any]]:
        """Locate plan explicitly by ID or by active session/source."""
        if plan_id:
            found = load_plan(plan_id, base_dir=self.base_dir)
            if found:
                return found
        ctx = resolve_active_session_context()
        eff_source = str(source_id or ctx["session_id"] or "").strip()
        if eff_source:
            found = find_latest_plan_for_source(eff_source, base_dir=self.base_dir)
            if found:
                return found
        return None

    def approve_plan(self, plan_id: str, edited_steps: Optional[Any] = None) -> Dict[str, Any]:
        """Approve an awaiting plan (unblocking live chat execution if waiting)."""
        with self._lock:
            plan = load_plan(plan_id, base_dir=self.base_dir)
            if not plan:
                return {"ok": False, "error": "Plan not found"}
            if has_pending_approval(plan_id):
                submit_approval_decision(plan_id, approved=True, edited_steps=edited_steps)
                return {"ok": True, "plan_id": plan_id, "resumed_gate": True}
            if edited_steps:
                plan["steps"] = normalize_steps(edited_steps)
            plan["status"] = "running"
            if plan["steps"] and not any(st.get("status") == "running" for st in plan["steps"]):
                for st in plan["steps"]:
                    if st.get("status") == "pending":
                        st["status"] = "running"
                        st["updated_at"] = time.time()
                        break
            save_plan(plan, base_dir=self.base_dir)
        emit_plan_event("plan_approved", plan)
        return {"ok": True, "plan_id": plan_id, "resumed_gate": False, "plan": plan}

    def reject_plan(self, plan_id: str, reason: str = "cancelled by user") -> Dict[str, Any]:
        """Reject/cancel an awaiting or active plan."""
        with self._lock:
            plan = load_plan(plan_id, base_dir=self.base_dir)
            if not plan:
                return {"ok": False, "error": "Plan not found"}
            if has_pending_approval(plan_id):
                submit_approval_decision(plan_id, approved=False, reason=reason)
                return {"ok": True, "plan_id": plan_id, "resumed_gate": True}
            plan["status"] = "cancelled"
            plan["summary"] = str(reason)[:300]
            save_plan(plan, base_dir=self.base_dir)
        emit_plan_event("plan_rejected", plan)
        return {"ok": True, "plan_id": plan_id, "resumed_gate": False, "plan": plan}

    def get_plan(self, plan_id: str = "", source_id: str = "") -> Optional[Dict[str, Any]]:
        return self.resolve_plan(plan_id=plan_id, source_id=source_id)

    def list_all(self, *, scope: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> list:
        return list_plans(scope=scope, status=status, limit=limit, base_dir=self.base_dir)

    def remove_plan(self, plan_id: str) -> bool:
        return delete_plan(plan_id, base_dir=self.base_dir)

    @staticmethod
    def format_plan_summary(plan: Dict[str, Any]) -> str:
        """Format compact multi-step checklist summary for LLM prompts and tool outputs."""
        if not isinstance(plan, dict):
            return ""
        prog = compute_plan_progress(plan)
        rev = int(plan.get("revision") or 1)
        rev_suffix = f", rev=v{rev}" if rev > 1 else ""
        lines = [
            f"Action Plan [{plan.get('plan_id')}] — {plan.get('title')} "
            f"(status={plan.get('status')}{rev_suffix}, progress={prog['done']}/{prog['total']} · {prog['percent']}%):"
        ]
        icons = {"done": "[✓]", "running": "[▶]", "failed": "[✗]", "skipped": "[-]", "pending": "[ ]"}
        for s in plan.get("steps") or []:
            mark = icons.get(s.get("status", "pending"), "[ ]")
            files_list = s.get("files") or []
            files_part = f" [files: {', '.join(files_list[:4])}]" if files_list else ""
            note = f" — {s['notes']}" if s.get("notes") else ""
            lines.append(f"  {mark} Step {s['index']}: {s['title']}{files_part}{note}")
        return "\n".join(lines)

    @staticmethod
    def format_plan_blueprint_for_coder(plan: Dict[str, Any], max_chars: int = 5500) -> str:
        """Format both checklist status and architectural blueprint for Coder execution turns."""
        if not isinstance(plan, dict):
            return ""
        summary = ActionPlanManager.format_plan_summary(plan)
        blueprint_parts = []
        goal = str(plan.get("goal") or "").strip()
        md = str(plan.get("plan_markdown") or "").strip()
        verif = str(plan.get("verification_plan") or "").strip()

        if md:
            blueprint_parts.append(md)
        else:
            if goal:
                blueprint_parts.append(f"Goal: {goal}")
            detail_lines = []
            for s in plan.get("steps") or []:
                files = s.get("files") or []
                det = str(s.get("details") or "").strip()
                if files or det:
                    line = f"- Step {s.get('index')} ({s.get('title')}):"
                    if files:
                        line += f" files={', '.join(files)}"
                    if det:
                        line += f" | {det}"
                    detail_lines.append(line)
            if detail_lines:
                blueprint_parts.append("Step Specifications:\n" + "\n".join(detail_lines))

        if verif and verif.lower()[:40] not in "\n".join(blueprint_parts).lower():
            blueprint_parts.append(f"Verification Plan:\n{verif}")

        blueprint_text = "\n\n".join(p for p in blueprint_parts if p.strip()).strip()
        if not blueprint_text:
            return summary

        budget = max(800, int(max_chars or 5500) - len(summary) - 80)
        if len(blueprint_text) > budget:
            blueprint_text = blueprint_text[:budget].rstrip() + "\n... [blueprint truncated for context budget]"

        return (
            f"{summary}\n\n"
            f"### ARCHITECTURAL BLUEPRINT (FOLLOW THESE SPECS) ###\n"
            f"{blueprint_text}"
        )

    def ensure_fallback_plan_from_text(
        self,
        *,
        user_text: str,
        assistant_text: str,
        source_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Extract numbered/bulleted steps from plain assistant text when Plan-Only mode was requested
        but the model responded in markdown without calling `ACTION_PLANS__create_plan`.
        Preserves the full markdown blueprint so the UI and Coder keep all architectural detail.
        """
        import re

        raw = str(assistant_text or "").strip()
        if not raw:
            return None

        extracted_steps = []
        for line in raw.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("```"):
                continue
            m = re.match(r"^(?:(?:\d+|[a-zA-Z])[.)]|[-*•]|#{2,4}\s+(?:Step\s+\d+[:.-]?|\d+[.)]))\s+(.+)$", clean, re.IGNORECASE)
            if m:
                step_txt = re.sub(r"\*\*([^*]+)\*\*", r"\1", m.group(1)).strip()
                if len(step_txt) >= 5 and len(extracted_steps) < 12:
                    extracted_steps.append(step_txt[:220])

        if len(extracted_steps) < 2:
            # Fallback: construct basic 3-step structure from the user request
            clean_req = re.sub(r"^/\w+\s*", "", str(user_text or "").strip()).strip()
            short_req = (clean_req[:120] + "...") if len(clean_req) > 120 else (clean_req or "Requested task")
            extracted_steps = [
                f"Analyze requirements and project structure for: {short_req}",
                "Implement core modules and application files in workspace",
                "Run syntax/test verification and summarize generated file links",
            ]

        clean_title = re.sub(r"^/\w+\s*", "", str(user_text or "").strip()).strip()
        title = (clean_title[:90] if clean_title else "Execution Plan")

        ctx = resolve_active_session_context()
        revise_target = str(ctx.get("turn_revise_plan_id") or "").strip()
        if revise_target:
            res = self.revise_plan(
                plan_id=revise_target,
                plan_markdown=raw,
                steps=extracted_steps,
                revision_note=clean_title[:240] or "Revised from text response",
                source_id=source_id,
                keep_awaiting_approval=True,
            )
            return res.get("plan") if isinstance(res, dict) else None

        res = self.create_plan(
            title=title,
            steps=extracted_steps,
            scope="agent",
            source_id=source_id,
            plan_markdown=raw,
            require_approval=True,
            wait_for_approval=False,
            metadata={"plan_only": True, "auto_extracted": True},
        )
        return res.get("plan") if isinstance(res, dict) else None

    def export_plan(self, plan_id: str, fmt: str = "md") -> Dict[str, Any]:
        """Serialize an existing plan for export as Markdown (.md), HTML (.html), YAML (.yaml), or JSON (.json)."""
        from hecos.core.action_plans.io_codec import normalize_export_format, serialize_plan_for_export

        plan = self.get_plan(plan_id=plan_id)
        if not plan:
            return {"ok": False, "error": f"Plan '{plan_id}' not found"}
        clean_fmt = normalize_export_format(fmt)
        content, mime, filename = serialize_plan_for_export(plan, fmt=clean_fmt)
        return {
            "ok": True,
            "plan_id": plan["plan_id"],
            "format": clean_fmt,
            "mime": mime,
            "filename": filename,
            "content": content,
        }

    def import_plan(
        self,
        *,
        content: Optional[str] = None,
        file_path: Optional[str] = None,
        filename: str = "",
        source_id: str = "",
        scope: str = "agent",
        reset_progress: bool = False,
    ) -> Dict[str, Any]:
        """Import a saved JSON (.hecos-plan.json / .json) or Markdown (.md) plan into the session."""
        import os
        from hecos.core.action_plans.io_codec import parse_imported_plan_content

        raw_text = content
        eff_filename = str(filename or "").strip()
        if file_path:
            if not os.path.isfile(file_path):
                return {"ok": False, "error": f"File not found: {file_path}"}
            if not eff_filename:
                eff_filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8-sig") as fh:
                raw_text = fh.read()

        if not raw_text or not str(raw_text).strip():
            return {"ok": False, "error": "Empty plan content"}

        try:
            parsed = parse_imported_plan_content(
                str(raw_text),
                filename=eff_filename,
                reset_progress=bool(reset_progress),
            )
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

        ctx = resolve_active_session_context()
        eff_source = str(source_id or ctx["session_id"] or "").strip()

        meta = dict(parsed.get("metadata") or {})
        meta["plan_only"] = True
        if eff_filename:
            meta["imported_from"] = eff_filename
        if file_path:
            meta["imported_path"] = os.path.abspath(file_path)

        plan = new_plan_dict(
            title=parsed["title"],
            steps=parsed["steps"],
            scope=scope,
            source_id=eff_source,
            plan_mode="plan_only",
            status="awaiting_approval",
            goal=parsed.get("goal", ""),
            plan_markdown=parsed.get("plan_markdown", ""),
            verification_plan=parsed.get("verification_plan", ""),
            metadata=meta,
        )
        plan["revision"] = max(1, int(parsed.get("revision") or 1))
        history = list(parsed.get("revision_history") or [])
        history.append({
            "revision": plan["revision"],
            "note": f"Imported from {eff_filename or 'file'}",
            "timestamp": time.time(),
        })
        plan["revision_history"] = history[-20:]

        with self._lock:
            if eff_source:
                prev = find_latest_plan_for_source(
                    eff_source, scope=scope, statuses=ACTIVE_PLAN_STATUSES, base_dir=self.base_dir
                )
                if prev and prev.get("plan_id") != plan["plan_id"]:
                    prev["status"] = "cancelled"
                    prev["summary"] = f"Superseded by imported plan {plan['plan_id']}"
                    prev["updated_at"] = time.time()
                    save_plan(prev, base_dir=self.base_dir)
            save_plan(plan, base_dir=self.base_dir)

        emit_plan_event("imported", plan)
        return {"ok": True, "plan": plan, "filename": eff_filename}


_MANAGER_SINGLETON: Optional[ActionPlanManager] = None
_MANAGER_LOCK = threading.Lock()


def get_action_plan_manager() -> ActionPlanManager:
    """Return process-wide singleton ActionPlanManager instance."""
    global _MANAGER_SINGLETON
    with _MANAGER_LOCK:
        if _MANAGER_SINGLETON is None:
            _MANAGER_SINGLETON = ActionPlanManager()
        return _MANAGER_SINGLETON
