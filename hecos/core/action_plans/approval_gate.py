"""
hecos/core/action_plans/approval_gate.py
Cooperative pause/resume gate when Action Plan execution requires user confirmation.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional

from hecos.core.action_plans.events import emit_plan_event

_GATE_LOCK = threading.Lock()
_PENDING_GATES: Dict[str, Dict[str, Any]] = {}


def register_pending_approval(plan_id: str) -> threading.Event:
    """Register an approval wait Event for `plan_id`."""
    ev = threading.Event()
    with _GATE_LOCK:
        _PENDING_GATES[plan_id] = {
            "event": ev,
            "decision": None,  # True = approved, False = rejected
            "edited_steps": None,
            "reason": "",
            "created_at": time.time(),
        }
    return ev


def has_pending_approval(plan_id: str) -> bool:
    """Return True if a worker thread is currently waiting on `plan_id`."""
    with _GATE_LOCK:
        return plan_id in _PENDING_GATES


def submit_approval_decision(
    plan_id: str,
    *,
    approved: bool,
    edited_steps: Optional[Any] = None,
    reason: str = "",
) -> bool:
    """Unblock waiting execution for `plan_id` with user's decision."""
    with _GATE_LOCK:
        entry = _PENDING_GATES.get(plan_id)
        if not entry:
            return False
        entry["decision"] = bool(approved)
        entry["edited_steps"] = edited_steps
        entry["reason"] = str(reason or "")
        entry["event"].set()
        return True


def cancel_pending_approval(plan_id: str, reason: str = "cancelled") -> bool:
    """Force-unblock a pending approval gate as rejected."""
    return submit_approval_decision(plan_id, approved=False, reason=reason)


def _ping_inference_watchdog() -> None:
    try:
        from hecos.core.agent.trace_session import get_active_session
        sess = get_active_session()
        if sess is not None and sess.trace_callback is not None:
            sess.trace_callback({"type": "heartbeat"}, "info")
    except Exception:
        pass


def await_plan_approval(
    plan: Dict[str, Any],
    *,
    timeout_sec: float = 300.0,
    abort_checker: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Wait until user approves/rejects `plan`, stop is requested, or timeout expires.
    Returns dict: {"approved": bool, "edited_steps": Any, "reason": str}.
    """
    pid = str(plan.get("plan_id") or "")
    ev = register_pending_approval(pid)
    emit_plan_event("approval_required", plan)

    deadline = time.monotonic() + max(5.0, float(timeout_sec or 300.0))
    last_hb = time.monotonic()

    try:
        while not ev.wait(timeout=0.4):
            if abort_checker and abort_checker():
                return {"approved": False, "edited_steps": None, "reason": "aborted_by_user"}
            now = time.monotonic()
            if now >= deadline:
                return {"approved": False, "edited_steps": None, "reason": "approval_timeout"}
            if now - last_hb >= 2.0:
                _ping_inference_watchdog()
                last_hb = now

        with _GATE_LOCK:
            entry = _PENDING_GATES.get(pid, {})
            return {
                "approved": bool(entry.get("decision")),
                "edited_steps": entry.get("edited_steps"),
                "reason": str(entry.get("reason") or ""),
            }
    finally:
        with _GATE_LOCK:
            _PENDING_GATES.pop(pid, None)
