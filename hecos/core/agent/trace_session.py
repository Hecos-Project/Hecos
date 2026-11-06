"""
hecos/core/agent/trace_session.py
Thread-safe session state and step containers for the Agent Trace system.
"""

import contextvars
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class TraceSession:
    """Holds structured step state for a single agentic turn."""

    def __init__(
        self,
        state_manager=None,
        trace_callback: Optional[Callable] = None,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.state_manager = state_manager
        self.trace_callback = trace_callback
        self.session_id = session_id
        self.config = config or {}
        self.t_turn_start = time.monotonic()
        self.steps: List[Dict[str, Any]] = []
        self.current_step: Optional[Dict[str, Any]] = None
        self._lock = threading.RLock()
        self._step_seq = 0

    def next_step_id(self) -> str:
        with self._lock:
            self._step_seq += 1
            return f"step_{self._step_seq}"

    def elapsed_ms(self) -> int:
        return max(0, int((time.monotonic() - self.t_turn_start) * 1000))


# Context variable and fallback thread-safe session pointers
_SESSION_VAR: contextvars.ContextVar[Optional[TraceSession]] = contextvars.ContextVar(
    "hecos_trace_session", default=None
)
_ACTIVE_SESSION_LOCK = threading.RLock()
_ACTIVE_SESSION: Optional[TraceSession] = None


def bind_session(
    state_manager=None,
    trace_callback: Optional[Callable] = None,
    session_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> TraceSession:
    """Starts and binds a new TraceSession for the current agentic turn."""
    global _ACTIVE_SESSION
    sess = TraceSession(
        state_manager=state_manager,
        trace_callback=trace_callback,
        session_id=session_id,
        config=config,
    )
    _SESSION_VAR.set(sess)
    with _ACTIVE_SESSION_LOCK:
        _ACTIVE_SESSION = sess
    return sess


def get_active_session() -> Optional[TraceSession]:
    """Retrieves the active TraceSession from contextvars or thread fallback."""
    sess = _SESSION_VAR.get()
    if sess is not None:
        return sess
    with _ACTIVE_SESSION_LOCK:
        return _ACTIVE_SESSION


def unbind_session() -> None:
    """Unbinds the active session."""
    global _ACTIVE_SESSION
    _SESSION_VAR.set(None)
    with _ACTIVE_SESSION_LOCK:
        _ACTIVE_SESSION = None


def build_turn_meta(sess: Optional[TraceSession], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Builds metadata for trace events sent to the WebUI."""
    return {
        "step_count": len(sess.steps) if sess else 1,
        "elapsed_ms": sess.elapsed_ms() if sess else 0,
        "trace_mode": cfg.get("trace_mode", "detailed"),
        "trace_after_done": cfg.get("trace_after_done", "summary"),
        "trace_show_args": cfg.get("trace_show_args", True),
        "action_console_mode": cfg.get("action_console_mode", "inline"),
    }


def public_step(step: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a JSON-safe copy of a step dict (without internal monotonic timestamps)."""
    return {k: v for k, v in step.items() if not k.startswith("_")}

