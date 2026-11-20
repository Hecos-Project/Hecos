"""
hecos/core/action_plans/events.py
Unified event broadcaster for Action Plans across WebUI SSE, StateManager, and EventBus.
"""

from __future__ import annotations

import time
from typing import Any, Dict


def emit_plan_event(event_kind: str, plan: Dict[str, Any]) -> None:
    """Emit structured `action_plan` updates to active chat SSE and global Hecos events."""
    payload: Dict[str, Any] = {
        "type": "action_plan",
        "event": str(event_kind or "updated"),
        "plan_id": plan.get("plan_id"),
        "source_id": plan.get("source_id"),
        "scope": plan.get("scope", "agent"),
        "status": plan.get("status", "running"),
        "plan": plan,
        "ts": time.time(),
    }

    # 1. Active AgentExecutor turn SSE callback (keeps inference watchdog alive too)
    try:
        from hecos.core.agent.trace_session import get_active_session
        sess = get_active_session()
        if sess is not None and sess.trace_callback is not None:
            sess.trace_callback(payload, "info")
        elif sess is not None and sess.state_manager is not None and hasattr(sess.state_manager, "add_event"):
            sess.state_manager.add_event("action_plan", payload)
    except Exception:
        pass

    # 2. Central Hecos event bus (for WebUI extensions, Flows UI, or listeners)
    try:
        from hecos.core.events import emit
        emit("action_plan_updated", payload)
    except Exception:
        pass
