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
            return {
                "session_id": str(sess.session_id or ""),
                "has_trace_callback": sess.trace_callback is not None,
                "state_manager": sess.state_manager,
            }
    except Exception:
        pass
    return {"session_id": "", "has_trace_callback": False, "state_manager": None}


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
        require_approval: Optional[bool] = None,
        wait_for_approval: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and persist a structured Action Plan, optionally awaiting user confirmation."""
        cfg = get_action_plans_config()
        ctx = resolve_active_session_context()
        eff_source = str(source_id or ctx["session_id"] or "").strip()

        if require_approval is None:
            needs_approval = (cfg.get("plan_mode") == "confirm")
        else:
            needs_approval = bool(require_approval)

        initial_status = "awaiting_approval" if (needs_approval and wait_for_approval and ctx["has_trace_callback"]) else (
            "awaiting_approval" if (needs_approval and not wait_for_approval) else "running"
        )
        plan = new_plan_dict(
            title=title,
            steps=steps,
            scope=scope,
            source_id=eff_source,
            plan_mode=cfg.get("plan_mode", "auto"),
            status=initial_status,
            metadata=metadata,
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
        return {"ok": True, "approved": plan["status"] == "running", "plan": plan}

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

    def complete_plan(
        self,
        *,
        plan_id: str = "",
        status: str = "completed",
        summary: str = "",
        source_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Finalize an Action Plan and emit completion notification."""
        target_status = str(status or "completed").strip().lower()
        if target_status not in PLAN_STATUSES:
            target_status = "completed"

        with self._lock:
            plan = self.resolve_plan(plan_id=plan_id, source_id=source_id)
            if not plan:
                return None
            if target_status == "completed":
                for st in plan.get("steps") or []:
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
            if plan["steps"] and plan["steps"][0]["status"] == "pending":
                plan["steps"][0]["status"] = "running"
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
        lines = [
            f"Action Plan [{plan.get('plan_id')}] — {plan.get('title')} "
            f"(status={plan.get('status')}, progress={prog['done']}/{prog['total']} · {prog['percent']}%):"
        ]
        icons = {"done": "[✓]", "running": "[▶]", "failed": "[✗]", "skipped": "[-]", "pending": "[ ]"}
        for s in plan.get("steps") or []:
            mark = icons.get(s.get("status", "pending"), "[ ]")
            note = f" — {s['notes']}" if s.get("notes") else ""
            lines.append(f"  {mark} Step {s['index']}: {s['title']}{note}")
        return "\n".join(lines)


_MANAGER_SINGLETON: Optional[ActionPlanManager] = None
_MANAGER_LOCK = threading.Lock()


def get_action_plan_manager() -> ActionPlanManager:
    """Return process-wide singleton ActionPlanManager instance."""
    global _MANAGER_SINGLETON
    with _MANAGER_LOCK:
        if _MANAGER_SINGLETON is None:
            _MANAGER_SINGLETON = ActionPlanManager()
        return _MANAGER_SINGLETON
