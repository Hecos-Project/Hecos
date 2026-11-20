"""
hecos/core/agent/turn_control.py
Per-turn cancellation registry and in-flight HTTP abort hooks for AgentExecutor & LLM backends.

Guarantees:
1. Each inference turn gets an immutable `threading.Event` (`cancel_event`) that is NEVER reset
   once set — avoiding race conditions where starting a new turn or closing SSE un-cancels an
   older background thread.
2. Starting a new turn on the same `session_id` automatically cancels & supersedes any prior
   in-flight turn for that session.
3. Registered socket/transport abort hooks fire immediately on cancel so blocked Ollama calls
   terminate cleanly without hogging GPU slots.
"""

from __future__ import annotations

import threading
import uuid
from typing import Callable, Dict, List, Optional, Tuple


class _TurnRecord:
    __slots__ = ("turn_id", "session_id", "cancel_event", "abort_hooks", "cancelled_by_user")

    def __init__(self, turn_id: str, session_id: str, cancel_event: threading.Event):
        self.turn_id = turn_id
        self.session_id = session_id
        self.cancel_event = cancel_event
        self.abort_hooks: List[Callable[[], None]] = []
        self.cancelled_by_user = False


_LOCK = threading.RLock()
_ACTIVE_TURNS: Dict[str, _TurnRecord] = {}
_EVENT_TO_TURN: Dict[int, _TurnRecord] = {}
_LATEST_SESSION_TURN: Dict[str, str] = {}


def _fire_abort_hooks(record: _TurnRecord) -> None:
    hooks = list(record.abort_hooks)
    record.abort_hooks.clear()
    for hook in hooks:
        try:
            hook()
        except Exception:
            pass


def register_turn(session_id: Optional[str]) -> Tuple[str, threading.Event]:
    """
    Cancel any prior active turn on `session_id`, then allocate and register a fresh
    `(turn_id, cancel_event)` pair.
    """
    sid = str(session_id or "").strip()
    if sid:
        cancel_session_turns(sid, by_user=False)

    ev = threading.Event()
    turn_id = f"{(sid or 'anon')[:16]}_{uuid.uuid4().hex[:10]}"
    rec = _TurnRecord(turn_id=turn_id, session_id=sid, cancel_event=ev)
    with _LOCK:
        _ACTIVE_TURNS[turn_id] = rec
        _EVENT_TO_TURN[id(ev)] = rec
        if sid:
            _LATEST_SESSION_TURN[sid] = turn_id
    return turn_id, ev


def cancel_session_turns(session_id: Optional[str], *, by_user: bool = True) -> int:
    """Cancel all active turns associated with `session_id` and fire their abort hooks."""
    sid = str(session_id or "").strip()
    if not sid:
        return 0
    targets: List[_TurnRecord] = []
    with _LOCK:
        for rec in _ACTIVE_TURNS.values():
            if rec.session_id == sid:
                if by_user:
                    rec.cancelled_by_user = True
                rec.cancel_event.set()
                targets.append(rec)
    for rec in targets:
        _fire_abort_hooks(rec)
    return len(targets)


def cancel_all_turns(*, by_user: bool = True) -> int:
    """Cancel every currently active inference turn across all sessions (called on Stop/ESC)."""
    with _LOCK:
        targets = list(_ACTIVE_TURNS.values())
        for rec in targets:
            if by_user:
                rec.cancelled_by_user = True
            rec.cancel_event.set()
    for rec in targets:
        _fire_abort_hooks(rec)
    return len(targets)


def register_abort_hook(cancel_event: Optional[threading.Event], hook: Callable[[], None]) -> bool:
    """
    Attach a transport abort callback (e.g., socket shutdown/close) to a turn's `cancel_event`.
    If `cancel_event` is already set, fires `hook()` immediately and returns False.
    """
    if cancel_event is None or not callable(hook):
        return True
    if cancel_event.is_set():
        try:
            hook()
        except Exception:
            pass
        return False

    with _LOCK:
        rec = _EVENT_TO_TURN.get(id(cancel_event))
        if rec is None:
            # Unregistered standalone Event: let caller check manually
            return True
        if rec.cancel_event.is_set():
            should_fire_now = True
        else:
            rec.abort_hooks.append(hook)
            should_fire_now = False

    if should_fire_now:
        try:
            hook()
        except Exception:
            pass
        return False
    return True


def unregister_abort_hook(cancel_event: Optional[threading.Event], hook: Callable[[], None]) -> None:
    """Detach a completed transport abort callback cleanly."""
    if cancel_event is None:
        return
    with _LOCK:
        rec = _EVENT_TO_TURN.get(id(cancel_event))
        if rec is not None and hook in rec.abort_hooks:
            try:
                rec.abort_hooks.remove(hook)
            except ValueError:
                pass


def is_turn_superseded(session_id: Optional[str], turn_id: Optional[str]) -> bool:
    """Return True if a newer turn has already started for the same `session_id`."""
    sid = str(session_id or "").strip()
    tid = str(turn_id or "").strip()
    if not sid or not tid:
        return False
    with _LOCK:
        latest = _LATEST_SESSION_TURN.get(sid)
        return bool(latest and latest != tid)


def complete_turn(turn_id: Optional[str]) -> None:
    """Remove `turn_id` from active registry (leaves its Event state untouched)."""
    tid = str(turn_id or "").strip()
    if not tid:
        return
    with _LOCK:
        rec = _ACTIVE_TURNS.pop(tid, None)
        if rec is not None:
            rec.abort_hooks.clear()
            _EVENT_TO_TURN.pop(id(rec.cancel_event), None)


def has_active_turns(session_id: Optional[str] = None) -> bool:
    """Return True if at least one non-cancelled inference turn is currently running."""
    sid = str(session_id or "").strip() if session_id else ""
    with _LOCK:
        for rec in _ACTIVE_TURNS.values():
            if sid and rec.session_id != sid:
                continue
            if not rec.cancel_event.is_set():
                return True
        return False
