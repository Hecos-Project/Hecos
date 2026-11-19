"""
hecos/modules/action_plans/main.py
Core Module facade exposing Hecos Action Plans to the capability scanner, LLM tools, and Flows.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from hecos.core.action_plans import build_plan_markdown_document, get_action_plan_manager


def _format_plan_only_tool_output(plan: dict, *, revised: bool = False) -> str:
    """Format rich Antigravity-style Implementation Plan output + compact voice/UI metadata."""
    marker = "[ACTION_PLAN REVISED — PLAN-ONLY MODE]" if revised else "[ACTION_PLAN CREATED — PLAN-ONLY MODE]"
    meta_json = json.dumps(
        {
            "plan_id": str(plan.get("plan_id") or ""),
            "title": str(plan.get("title") or "Implementation Plan"),
            "steps_count": len(plan.get("steps") or []),
            "revision": int(plan.get("revision") or 1),
            "revised": bool(revised),
        },
        ensure_ascii=False,
    )
    rendered_doc = build_plan_markdown_document(plan, include_step_checklist=True)
    action_note = (
        f"The Implementation Plan (v{plan.get('revision', 1)}) has been updated and refreshed in the user's Action Plan card."
        if revised
        else "The Implementation Plan has been saved and displayed in the user's Action Plan card with 'View Plan', 'Revise', 'Execute Plan', and 'Run with Coder' controls."
    )
    return (
        f"{marker}\n"
        f"<!--PLAN_META:{meta_json}-->\n"
        f"{rendered_doc}\n\n"
        f"[SYSTEM: {action_note} "
        "Do NOT call file-writing or execution tools (`EXECUTOR__write_file`, `patch_file`, `start_app`, etc.) in this turn. "
        "Conclude your response now.]"
    )


class ActionPlansTools:
    """Native .tools interface for shared Hecos Action Plans."""

    def __init__(self):
        self.tag = "ACTION_PLANS"
        self.desc = "Shared Core multi-step Action Plans, Antigravity-style Implementation Plans, interactive revision, and execution checkpoints."
        self.status = "ONLINE (Core Module Active)"
        self.icon = "fas fa-list-check"
        self.category = "SISTEMA"

    def create_plan(
        self,
        title: str,
        steps: Any,
        plan_markdown: str = "",
        goal: str = "",
        verification_plan: str = "",
        require_approval: Optional[bool] = None,
        scope: str = "agent",
        source_id: str = "",
    ) -> str:
        """Create a structured Antigravity-style Implementation Plan & executable step checklist.
        :param title: Concise title of the Implementation Plan.
        :param steps: JSON array of ordered step objects [{"title": "...", "files": ["[NEW] path/file.py"], "details": "..."}] or step description strings.
        :param plan_markdown: Full Implementation Plan in rich Markdown with sections: ## Goal & Context, ## Architecture & Key Decisions, ## Proposed Changes (grouped by component with [NEW]/[MODIFY]/[DELETE] file paths, routes, schemas, functions), ## Verification Plan (tests & checks), and optional ## Open Questions.
        :param goal: Concise 1-3 sentence technical objective & problem statement.
        :param verification_plan: Concrete automated test suite, commands, and runtime checks to verify the implementation.
        :param require_approval: Optional boolean to require user approval before executing steps.
        :param scope: Plan scope ('agent' or 'flow').
        :param source_id: Optional session or flow run ID.
        """
        mgr = get_action_plan_manager()
        res = mgr.create_plan(
            title=title,
            steps=steps,
            scope=scope,
            source_id=source_id,
            goal=goal,
            plan_markdown=plan_markdown,
            verification_plan=verification_plan,
            require_approval=require_approval,
        )
        plan = res.get("plan") or {}
        if res.get("plan_only") or plan.get("plan_mode") == "plan_only":
            return _format_plan_only_tool_output(plan, revised=bool(res.get("revised")))
        if not res.get("ok") or not res.get("approved"):
            reason = res.get("reason") or "cancelled"
            return (
                f"[ACTION_PLAN REJECTED] Plan '{plan.get('plan_id')}' was not approved ({reason}). "
                f"Do NOT proceed with mutating steps; inform the user and wait for new instructions."
            )
        summary = mgr.format_plan_summary(plan)
        prefix = "[ACTION_PLAN APPROVED]" if plan.get("plan_mode") == "confirm" else "[ACTION_PLAN CREATED]"
        return f"{prefix}\n{summary}"

    def revise_plan(
        self,
        revision_note: str,
        title: str = "",
        plan_markdown: str = "",
        steps: Any = None,
        goal: str = "",
        verification_plan: str = "",
        plan_id: str = "",
    ) -> str:
        """Revise the active Implementation Plan in-place according to user feedback without editing code files yet.
        :param revision_note: Brief summary of what changed in this revision based on user feedback.
        :param title: Optional updated plan title.
        :param plan_markdown: Updated full Implementation Plan in rich Markdown reflecting the requested changes while preserving unaffected sections.
        :param steps: Updated JSON array of ordered step objects [{"title": "...", "files": [...], "details": "..."}] or strings matching the revised blueprint.
        :param goal: Optional updated technical goal statement.
        :param verification_plan: Optional updated automated/manual verification plan.
        :param plan_id: Optional explicit plan ID (defaults to active session plan).
        """
        mgr = get_action_plan_manager()
        res = mgr.revise_plan(
            plan_id=plan_id,
            title=title or None,
            goal=goal or None,
            plan_markdown=plan_markdown or None,
            steps=steps,
            verification_plan=verification_plan or None,
            revision_note=revision_note,
            keep_awaiting_approval=True,
        )
        plan = res.get("plan") or {}
        return _format_plan_only_tool_output(plan, revised=True)

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
            "create_plan": "Create a structured Antigravity-style Implementation Plan and step checklist.",
            "revise_plan": "Revise the active Implementation Plan in-place according to user feedback.",
            "update_step": "Update a plan step status and progress notes.",
            "get_plan": "Inspect the current progress of an action plan.",
            "complete_plan": "Finalize the active action plan.",
        },
    }


def status():
    return tools.status


def get_plugin():
    return tools
