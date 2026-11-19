"""
hecos/core/agent/checkpointing/resume_builder.py
Reconstructs sanitized AgentExecutor loop state + ground-truth resume prompt from a checkpoint.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

from hecos.core.agent.checkpointing.disk_inspector import inspect_workspace_progress


def build_resume_state(checkpoint: Dict[str, Any], default_max_iterations: int = 25) -> Dict[str, Any]:
    """
    Build resumed iteration counter, context messages, tool results, and disk verification note
    from a saved session checkpoint.
    """
    user_text = str(checkpoint.get("user_text") or "")
    prev_iter = max(0, int(checkpoint.get("iteration") or 0))
    prev_max = int(checkpoint.get("max_iterations") or default_max_iterations)

    extra_steps = 10
    plan_summary_block = ""
    try:
        from hecos.core.action_plans import get_action_plans_config, get_action_plan_manager
        ap_cfg = get_action_plans_config()
        extra_steps = int(ap_cfg.get("resume_extra_steps", 10) or 10)
        mgr = get_action_plan_manager()
        linked_plan = mgr.resolve_plan(
            plan_id=str(checkpoint.get("plan_id") or ""),
            source_id=str(checkpoint.get("session_id") or ""),
        )
        if linked_plan and linked_plan.get("steps"):
            plan_summary_block = mgr.format_plan_summary(linked_plan)
    except Exception:
        pass

    # Guarantee enough remaining iterations to inspect disk, finish missing pieces, and run tests
    resumed_max = max(prev_max, default_max_iterations, prev_iter + max(1, extra_steps))

    agent_context: List[Dict[str, Any]] = copy.deepcopy(checkpoint.get("agent_context") or [])
    accumulated_tool_results: List[Dict[str, Any]] = copy.deepcopy(
        checkpoint.get("accumulated_tool_results") or []
    )
    retries_state = dict(checkpoint.get("retries_state") or {"stream": 0, "file": 0, "netsearch": 0})

    disk_snapshot = inspect_workspace_progress(accumulated_tool_results, user_text=user_text)
    project_dir = disk_snapshot.get("project_dir") or ""
    dir_entries = disk_snapshot.get("directory_entries") or []
    verified_files = disk_snapshot.get("verified_files") or []

    status_reason = str(checkpoint.get("reason") or checkpoint.get("status") or "interrupted").strip()
    lines = [
        f"[SYSTEM RESUME CHECKPOINT]: Previous execution was interrupted after Iteration {prev_iter}/{resumed_max} ({status_reason}).",
    ]
    if project_dir:
        lines.append(f"Project folder on disk: `{project_dir}`")
    if dir_entries:
        lines.append("Files currently present on disk right now: " + ", ".join(dir_entries[:25]))
    elif verified_files:
        lines.append(
            "Verified files created before interruption: "
            + ", ".join(f"{f['name']} ({f.get('size', 0)}B)" for f in verified_files[:20])
        )
    else:
        lines.append("No completed files verified on disk yet in this task.")

    if plan_summary_block:
        lines.append("Current Action Plan checklist (resume from the first unfinished step):\n" + plan_summary_block)

    lines.append(
        "Continue from this exact state: inspect existing files with `EXECUTOR__read_file` only if needed, "
        "do NOT rewrite files that are already complete and working, finish any missing files/tests, "
        "and run final verification (`EXECUTOR__run_project_test` / `EXECUTOR__start_app` / `EXECUTOR__probe_url`)."
    )
    agent_context.append({"role": "user", "content": "\n".join(lines)})

    return {
        "user_text": user_text,
        "start_iteration": prev_iter,
        "max_iterations": resumed_max,
        "agent_context": agent_context,
        "accumulated_tool_results": accumulated_tool_results,
        "retries_state": retries_state,
        "disk_snapshot": disk_snapshot,
    }
