"""
hecos/core/agent/traces.py
─────────────────────────────────────────────────────────────────────────────
Hecos Agent Trace Engine (Backend)
Manages per-turn execution traces, structured step timelines, live package
progress substeps, and Action Console events for both Terminal CLI and WebUI.
Delegates session state to trace_session.py and terminal rendering to trace_cli.py.
─────────────────────────────────────────────────────────────────────────────
"""

import os
import time
import threading
from contextlib import contextmanager
from typing import Optional, Callable, Dict, List, Any

from hecos.core.logging import logger
from hecos.core.agent.trace_session import (
    TraceSession,
    bind_session,
    get_active_session,
    unbind_session,
    build_turn_meta,
    public_step,
)
from hecos.core.agent.trace_cli import (
    COLOR_AGENT,
    COLOR_TOOL,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_RESET,
    safe_print,
    print_cli_trace,
    print_cli_action_box,
)

# Backward-compatible alias
_safe_print = safe_print

# ── Cached AgentConfig Loader (avoids reading agent.yaml on every step) ───────
_CFG_LOCK = threading.Lock()
_CACHED_CFG: Optional[Dict[str, Any]] = None
_CACHED_CFG_MTIME: float = 0.0
_AGENT_YAML_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "data", "agent.yaml")
)


def invalidate_agent_config_cache() -> None:
    """Forces reload of agent.yaml on next access (called after WebUI config save)."""
    global _CACHED_CFG_MTIME
    with _CFG_LOCK:
        _CACHED_CFG_MTIME = 0.0


def get_agent_config() -> Dict[str, Any]:
    """Returns the validated AgentConfig dict, cached by file mtime."""
    global _CACHED_CFG, _CACHED_CFG_MTIME
    with _CFG_LOCK:
        try:
            mtime = os.path.getmtime(_AGENT_YAML_PATH) if os.path.exists(_AGENT_YAML_PATH) else -1.0
            if _CACHED_CFG is not None and mtime == _CACHED_CFG_MTIME:
                return dict(_CACHED_CFG)
            from hecos.config.yaml_utils import load_yaml
            from hecos.config.schemas.agent_schema import AgentConfig
            if os.path.exists(_AGENT_YAML_PATH):
                model = load_yaml(_AGENT_YAML_PATH, AgentConfig)
            else:
                model = AgentConfig()
            _CACHED_CFG = model.model_dump()
            _CACHED_CFG_MTIME = mtime
            return dict(_CACHED_CFG)
        except Exception as e:
            logger.debug(f"[AgentTracer] Config load fallback: {e}")
            return {
                "enabled": True,
                "max_iterations": 15,
                "verbose_traces": True,
                "trace_mode": "detailed",
                "trace_after_done": "summary",
                "trace_show_args": True,
                "trace_persist_history": True,
                "cli_traces_enabled": True,
                "action_console_enabled": True,
                "action_console_mode": "inline",
            }


class AgentTracer:
    """
    Handles Live Execution Traces for the Agentic Loop.
    Supports both structured step timelines (`start_step`, `finish_step`, `progress`)
    and legacy string calls (`emit`, `emit_action`, `action_box`).
    """

    COLOR_AGENT = COLOR_AGENT
    COLOR_TOOL = COLOR_TOOL
    COLOR_ERROR = COLOR_ERROR
    COLOR_SUCCESS = COLOR_SUCCESS
    COLOR_RESET = COLOR_RESET

    _current_state_manager = None

    @classmethod
    def bind(
        cls,
        state_manager=None,
        trace_callback: Optional[Callable] = None,
        session_id: Optional[str] = None,
    ) -> TraceSession:
        """Starts and binds a new TraceSession for the current agentic turn."""
        cls._current_state_manager = state_manager
        cfg = get_agent_config()
        return bind_session(
            state_manager=state_manager,
            trace_callback=trace_callback,
            session_id=session_id,
            config=cfg,
        )

    @classmethod
    def get_session(cls) -> Optional[TraceSession]:
        return get_active_session()

    @classmethod
    def unbind(cls) -> None:
        unbind_session()

    @classmethod
    def _dispatch_to_ui(cls, sess: Optional[TraceSession], payload: Dict[str, Any], state_manager=None) -> None:
        """Routes trace payload to WebUI session SSE queue or global events queue."""
        cfg = sess.config if sess else get_agent_config()
        trace_mode = cfg.get("trace_mode", "detailed")
        if trace_mode == "off" or not cfg.get("verbose_traces", True):
            if payload.get("type") != "think":
                return

        if sess and sess.trace_callback:
            try:
                sess.trace_callback(payload, payload.get("level", "info"))
            except Exception as e:
                logger.debug(f"[AgentTracer] trace_callback error: {e}")
            return

        sm = state_manager or (sess.state_manager if sess else None) or cls._current_state_manager
        if sm and hasattr(sm, "add_event"):
            ev_type = payload.get("type", "agent_trace")
            sm.add_event(ev_type, payload)

    @classmethod
    def _print_cli(cls, msg: str, level: str = "info", sess: Optional[TraceSession] = None) -> None:
        cfg = sess.config if sess else get_agent_config()
        print_cli_trace(msg, level=level, cli_enabled=cfg.get("cli_traces_enabled", True))

    @classmethod
    def _build_turn_meta(cls, sess: Optional[TraceSession]) -> Dict[str, Any]:
        cfg = sess.config if sess else get_agent_config()
        return build_turn_meta(sess, cfg)

    @classmethod
    def _public_step(cls, step: Dict[str, Any]) -> Dict[str, Any]:
        return public_step(step)

    @classmethod
    def start_step(
        cls,
        kind: str,
        label: str,
        detail: str = "",
        args_preview: str = "",
        icon: str = "",
        level: str = "info",
        module_name: str = "",
        close_previous: bool = True,
    ) -> Dict[str, Any]:
        """Starts a new structured step in the current turn's timeline and emits it to UI + CLI."""
        sess = cls.get_session()
        now_mono = time.monotonic()

        if sess is None:
            sess = cls.bind(cls._current_state_manager)

        cfg = sess.config
        if not cfg.get("trace_show_args", True):
            args_preview = ""

        with sess._lock:
            if close_previous and sess.current_step and sess.current_step.get("status") == "running":
                prev = sess.current_step
                prev["status"] = "ok"
                prev["duration_ms"] = max(0, int((now_mono - prev.get("_t_mono", now_mono)) * 1000))

            default_icons = {
                "llm": "fa-brain",
                "tool": "fa-wrench",
                "vision": "fa-eye",
                "think": "fa-lightbulb",
                "command": "fa-bolt",
                "system": "fa-microchip",
                "error": "fa-circle-exclamation",
            }
            step = {
                "id": sess.next_step_id(),
                "kind": kind,
                "level": level,
                "label": label,
                "module_name": module_name or "",
                "detail": detail or "",
                "args_preview": args_preview or "",
                "result_preview": "",
                "icon": icon or default_icons.get(kind, "fa-circle-dot"),
                "status": "running",
                "t_start": sess.elapsed_ms(),
                "duration_ms": 0,
                "substeps": [],
                "actions": [],
                "_t_mono": now_mono,
            }
            sess.steps.append(step)
            sess.current_step = step
            pub_step = cls._public_step(step)

        display_msg = label
        if args_preview:
            display_msg += f" ({args_preview})"
        elif detail:
            display_msg += f" — {detail}"

        cls._print_cli(display_msg, level=level, sess=sess)
        cls._dispatch_to_ui(
            sess,
            {
                "type": "agent_trace",
                "level": level,
                "message": display_msg,
                "step": pub_step,
                "turn": cls._build_turn_meta(sess),
            },
        )
        return step

    @classmethod
    def update_step(
        cls,
        step: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None,
        detail: Optional[str] = None,
        result_preview: Optional[str] = None,
        status: Optional[str] = None,
        level: Optional[str] = None,
        add_substep: Optional[str] = None,
    ) -> None:
        """Updates the active (or specified) step and notifies the UI."""
        sess = cls.get_session()
        if not sess:
            return

        with sess._lock:
            target = step or sess.current_step
            if not target:
                return
            now_mono = time.monotonic()
            target["duration_ms"] = max(0, int((now_mono - target.get("_t_mono", now_mono)) * 1000))
            if label is not None:
                target["label"] = label
            if detail is not None:
                target["detail"] = detail
            if result_preview is not None:
                target["result_preview"] = result_preview
            if status is not None:
                target["status"] = status
            if level is not None:
                target["level"] = level
            if add_substep:
                clean_sub = add_substep.strip()
                if clean_sub and (not target["substeps"] or target["substeps"][-1] != clean_sub):
                    target["substeps"].append(clean_sub)
                target["detail"] = clean_sub
            pub_step = cls._public_step(target)

        display_msg = target["label"]
        if target.get("detail"):
            display_msg += f" — {target['detail']}"
        elif target.get("result_preview"):
            display_msg += f" → {target['result_preview']}"

        cls._dispatch_to_ui(
            sess,
            {
                "type": "agent_trace",
                "level": target.get("level", "info"),
                "message": display_msg,
                "step": pub_step,
                "turn": cls._build_turn_meta(sess),
            },
        )

    @classmethod
    def finish_step(
        cls,
        step: Optional[Dict[str, Any]] = None,
        status: str = "ok",
        result_preview: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Marks a step as finished ('ok' or 'error') with its measured duration."""
        sess = cls.get_session()
        if not sess:
            return

        with sess._lock:
            target = step or sess.current_step
            if not target:
                return
            now_mono = time.monotonic()
            target["duration_ms"] = max(0, int((now_mono - target.get("_t_mono", now_mono)) * 1000))
            target["status"] = status
            if status == "error":
                target["level"] = "error"
            if result_preview is not None:
                target["result_preview"] = result_preview
            if detail is not None:
                target["detail"] = detail
            if sess.current_step is target:
                sess.current_step = None
            pub_step = cls._public_step(target)

        display_msg = target["label"]
        if target.get("result_preview"):
            display_msg += f" — {target['result_preview']}"
        lvl = "error" if status == "error" else target.get("level", "info")
        cls._print_cli(f"{display_msg} ({target['duration_ms']}ms)", level=lvl, sess=sess)
        cls._dispatch_to_ui(
            sess,
            {
                "type": "agent_trace",
                "level": lvl,
                "message": display_msg,
                "step": pub_step,
                "turn": cls._build_turn_meta(sess),
            },
        )

    @classmethod
    @contextmanager
    def step(
        cls,
        kind: str,
        label: str,
        detail: str = "",
        args_preview: str = "",
        icon: str = "",
        level: str = "info",
        module_name: str = "",
    ):
        """Context manager that automatically measures duration and records exceptions."""
        s = cls.start_step(
            kind=kind,
            label=label,
            detail=detail,
            args_preview=args_preview,
            icon=icon,
            level=level,
            module_name=module_name,
        )
        try:
            yield s
        except Exception as exc:
            cls.finish_step(s, status="error", result_preview=str(exc))
            raise
        else:
            if s.get("status") == "running":
                cls.finish_step(s, status="ok")

    @classmethod
    def progress(cls, msg: str, pct: Optional[int] = None, level: str = "tool") -> None:
        """Live progress API for long-running packages (attaches sub-progress to running step)."""
        text = f"{msg} ({pct}%)" if pct is not None else str(msg)
        sess = cls.get_session()
        if sess and sess.current_step and sess.current_step.get("status") == "running":
            cls._print_cli(text, level=level, sess=sess)
            cls.update_step(sess.current_step, add_substep=text, level=level)
        else:
            cls.start_step(kind="tool", label=text, level=level, icon="fa-circle-notch")

    @staticmethod
    def emit(state_manager, msg: Any, level: str = "info") -> None:
        """Backward-compatible trace emitter used by AgentExecutor and plugins."""
        sess = AgentTracer.get_session()

        if isinstance(msg, dict):
            if msg.get("type") == "think":
                think_txt = str(msg.get("text") or "").strip()
                if think_txt and sess:
                    from hecos.core.agent.trace_labeler import tr
                    preview = (think_txt[:70].rstrip() + "…") if len(think_txt) > 70 else think_txt
                    s = AgentTracer.start_step(
                        kind="think",
                        label=tr("Ragionamento interno del modello", "Model internal reasoning"),
                        icon="fa-lightbulb",
                        level="info",
                    )
                    AgentTracer.finish_step(s, status="ok", result_preview=preview)
                if sess and sess.trace_callback:
                    try:
                        sess.trace_callback(msg, "think")
                    except Exception:
                        pass
                return
            AgentTracer._dispatch_to_ui(sess, msg, state_manager=state_manager)
            return

        text = str(msg or "").strip()
        if not text:
            return

        if sess and sess.current_step and sess.current_step.get("status") == "running":
            curr_kind = sess.current_step.get("kind")
            if curr_kind in ("tool", "vision") and level in ("tool", "info"):
                AgentTracer._print_cli(text, level=level, sess=sess)
                AgentTracer.update_step(sess.current_step, add_substep=text)
                return
            if level == "error":
                AgentTracer.finish_step(sess.current_step, status="error", result_preview=text)
                return

        if level == "success":
            if sess and sess.current_step and sess.current_step.get("status") == "running":
                AgentTracer.finish_step(sess.current_step, status="ok", result_preview=text)
            else:
                AgentTracer._print_cli(text, level="success", sess=sess)
                AgentTracer._dispatch_to_ui(
                    sess,
                    {
                        "type": "agent_trace",
                        "level": "success",
                        "message": text,
                        "turn": AgentTracer._build_turn_meta(sess),
                    },
                    state_manager=state_manager,
                )
            return

        kind = "error" if level == "error" else ("tool" if level == "tool" else "llm")
        icon = "fa-circle-exclamation" if level == "error" else ("fa-wrench" if level == "tool" else "fa-brain")
        step = AgentTracer.start_step(kind=kind, label=text, level=level, icon=icon)
        if level == "error":
            AgentTracer.finish_step(step, status="error", result_preview=text)

    @staticmethod
    def emit_action(tool_name: str, command: str, output: str = "", *extra, **kwargs) -> None:
        """Emits a physical tool execution log to the terminal and to the WebUI."""
        if extra and isinstance(extra[0], str):
            output = f"[{output}] {extra[0]}" if output else extra[0]

        sess = AgentTracer.get_session()
        cfg = sess.config if sess else get_agent_config()
        mode = cfg.get("action_console_mode", "inline")
        if not cfg.get("action_console_enabled", True) or mode == "off":
            return

        out_str = str(output or "").strip()
        preview = out_str[:500] + ("\n...[truncated]" if len(out_str) > 500 else "")

        # 1. Terminal Output
        print_cli_action_box(
            tool_name=str(tool_name or "SYSTEM"),
            command=str(command or ""),
            preview=preview,
            cli_enabled=cfg.get("cli_traces_enabled", True),
        )

        action_item = {
            "tool_name": str(tool_name or "SYSTEM"),
            "command": str(command or ""),
            "output": preview,
            "mode": mode,
        }

        # Attach to current step in timeline if available
        if sess:
            with sess._lock:
                target = sess.current_step or (sess.steps[-1] if sess.steps else None)
                if target is not None:
                    target.setdefault("actions", []).append(action_item)
                    pub_step = AgentTracer._public_step(target)
                else:
                    pub_step = None

            if pub_step is not None:
                AgentTracer._dispatch_to_ui(
                    sess,
                    {
                        "type": "agent_trace",
                        "level": "tool",
                        "message": f"{tool_name}: {command}",
                        "step": pub_step,
                        "action": action_item,
                        "turn": AgentTracer._build_turn_meta(sess),
                    },
                )

        # 2. If mode is 'chat', also emit legacy action_console event for separate chat bubble
        if mode == "chat":
            sm = (sess.state_manager if sess else None) or AgentTracer._current_state_manager
            if sm and hasattr(sm, "add_event"):
                sm.add_event("action_console", action_item)

    @staticmethod
    def action_box(
        source: Any = None,
        title: str = "ACTION",
        command: str = "",
        output: str = "",
        **kwargs,
    ) -> None:
        """Alias used by HPM packages to emit an Action Console box."""
        AgentTracer.emit_action(title or str(source or "ACTION"), command, output)

    @classmethod
    def finalize_turn(cls, final_message: Optional[str] = None, status: str = "ok") -> Dict[str, Any]:
        """Closes running steps and returns turn summary for SSE and DB persistence."""
        sess = cls.get_session()
        if not sess:
            return {}

        now_mono = time.monotonic()
        with sess._lock:
            if sess.current_step and sess.current_step.get("status") == "running":
                sess.current_step["status"] = "error" if status == "error" else "ok"
                sess.current_step["duration_ms"] = max(
                    0, int((now_mono - sess.current_step.get("_t_mono", now_mono)) * 1000)
                )
                sess.current_step = None

            total_ms = sess.elapsed_ms()
            tools_used = []
            has_error = (status == "error")
            pub_steps = []
            for s in sess.steps:
                if s.get("status") == "error":
                    has_error = True
                if s.get("kind") in ("tool", "command"):
                    mname = s.get("module_name") or s.get("label", "").split("·")[0].strip()
                    if mname and mname not in tools_used:
                        tools_used.append(mname)
                pub_steps.append(cls._public_step(s))

        if final_message:
            cls._print_cli(
                f"{final_message} ({total_ms / 1000.0:.1f}s)",
                level="error" if has_error else "success",
                sess=sess,
            )

        cfg = sess.config
        summary = {
            "total_steps": len(pub_steps),
            "tools_used": tools_used,
            "duration_ms": total_ms,
            "status": "error" if has_error else "ok",
            "trace_mode": cfg.get("trace_mode", "detailed"),
            "trace_after_done": cfg.get("trace_after_done", "summary"),
            "trace_show_args": cfg.get("trace_show_args", True),
            "steps": pub_steps,
        }
        return summary
