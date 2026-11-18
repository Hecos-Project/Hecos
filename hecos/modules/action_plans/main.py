"""
hecos/modules/action_plans/main.py
Core Module facade exposing Hecos Action Plans to the capability scanner, LLM tools, and Flows.
"""

from __future__ import annotations

from typing import Any, Optional

from hecos.core.action_plans import get_action_plan_manager


class ActionPlansTools:
    """Native .tools interface for shared Hecos Action Plans."""

    def __init__(self):
        self.tag = "ACTION_PLANS"
        self.desc = "Shared Core multi-step Action Plans, execution checkpoints, and step approval."
        self.status = "ONLINE (Core Module Active)"
        self.icon = "fas fa-list-check"
        self.category = "SISTEMA"

    def create_plan(
        self,
        title: str,
        steps: Any,
        require_approval: Optional[bool] = None,
        scope: str = "agent",
        source_id: str = "",
    ) -> str:
        """Create a structured multi-step action plan for the current task."""
        mgr = get_action_plan_manager()
        res = mgr.create_plan(
            title=title,
            steps=steps,
            scope=scope,
            source_id=source_id,
            require_approval=require_approval,
        )
        plan = res.get("plan") or {}
        if not res.get("ok") or not res.get("approved"):
            reason = res.get("reason") or "cancelled"
            return (
                f"[ACTION_PLAN REJECTED] Plan '{plan.get('plan_id')}' was not approved ({reason}). "
                f"Do NOT proceed with mutating steps; inform the user and wait for new instructions."
            )
        summary = mgr.format_plan_summary(plan)
        prefix = "[ACTION_PLAN APPROVED]" if plan.get("plan_mode") == "confirm" else "[ACTION_PLAN CREATED]"
        return f"{prefix}\n{summary}"

    def update_step(
        self,
        step_index: Any,
        status: str = "done",
        notes: str = "",
        plan_id: str = "",
    ) -> str:
        """Update status ('pending'|'running'|'done'|'skipped'|'failed') for a step."""
        mgr = get_action_plan_manager()
        updated = mgr.update_step(plan_id=plan_id, step_ref=step_index, status=status, notes=notes)
        if not updated:
            return "[ACTION_PLAN] No matching active plan or step found."
        return f"[ACTION_PLAN UPDATED]\n{mgr.format_plan_summary(updated)}"

    def get_plan(self, plan_id: str = "") -> str:
        """Return current step checklist and progress of the active Action Plan."""
        mgr = get_action_plan_manager()
        plan = mgr.get_plan(plan_id=plan_id)
        if not plan:
            return "[ACTION_PLAN] No active action plan found for this session."
        return mgr.format_plan_summary(plan)

    def complete_plan(self, summary: str = "", status: str = "completed", plan_id: str = "") -> str:
        """Finalize the active Action Plan once work and verification are complete."""
        mgr = get_action_plan_manager()
        done_plan = mgr.complete_plan(plan_id=plan_id, status=status, summary=summary)
        if not done_plan:
            return "[ACTION_PLAN] No active action plan found to complete."
        return f"[ACTION_PLAN FINALIZED]\n{mgr.format_plan_summary(done_plan)}"


tools = ActionPlansTools()


def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "commands": {
            "create_plan": "Create a structured multi-step action plan.",
            "update_step": "Update a plan step status and progress notes.",
            "get_plan": "Inspect the current progress of an action plan.",
            "complete_plan": "Finalize the active action plan.",
        },
    }


def status():
    return tools.status


def get_plugin():
    return tools
