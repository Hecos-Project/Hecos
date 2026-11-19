"""
hecos/modules/web_ui/agent_resume/routes.py
HTTP endpoints to inspect, dismiss, and resume interrupted AgentExecutor checkpoints.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Dict

from flask import jsonify, request

from hecos.core.agent.checkpointing import (
    inspect_workspace_progress,
    is_resumable_checkpoint,
    load_checkpoint,
    mark_checkpoint_status,
)


def _format_checkpoint_summary(ckpt: Dict[str, Any], running_now: bool) -> Dict[str, Any]:
    """Build a compact UI summary + live disk snapshot for the Resume banner."""
    user_text = str(ckpt.get("user_text") or "").strip()
    preview = (user_text[:180] + "...") if len(user_text) > 180 else user_text
    disk = inspect_workspace_progress(
        ckpt.get("accumulated_tool_results") or [],
        user_text=user_text,
    )
    return {
        "session_id": ckpt.get("session_id"),
        "status": ckpt.get("status", "running"),
        "reason": ckpt.get("reason", ""),
        "iteration": int(ckpt.get("iteration") or 0),
        "max_iterations": int(ckpt.get("max_iterations") or 25),
        "model_label": ckpt.get("model_label", ""),
        "user_preview": preview,
        "updated_at": float(ckpt.get("updated_at") or 0),
        "running_now": running_now,
        "project_dir": disk.get("project_dir") or "",
        "directory_entries": disk.get("directory_entries") or [],
        "verified_files": disk.get("verified_files") or [],
    }


def init_agent_resume_routes(app, cfg_mgr, logger) -> None:
    """Register /api/agent/checkpoints* endpoints for crash/timeout task recovery."""

    def _resolve_sid(explicit: str = "") -> str:
        clean = (explicit or "").strip()
        if clean:
            return clean
        try:
            from hecos.core.privacy import privacy_manager
            return str(privacy_manager.get_session_id() or "")
        except Exception:
            return ""

    @app.route("/api/agent/checkpoints", methods=["GET"])
    def api_get_agent_checkpoint():
        from hecos.modules.web_ui.routes_chat_inference import _sessions

        sid = _resolve_sid(request.args.get("session_id", ""))
        if not sid:
            return jsonify({"ok": True, "has_resumable": False, "checkpoint": None})

        try:
            from hecos.core.action_plans import get_action_plans_config
            ap_cfg = get_action_plans_config(cfg_mgr=cfg_mgr)
            if not ap_cfg.get("checkpoint_enabled", True) or not ap_cfg.get("resume_banner_enabled", True):
                return jsonify({"ok": True, "has_resumable": False, "checkpoint": None})
        except Exception:
            pass

        ckpt = load_checkpoint(sid)
        if not is_resumable_checkpoint(ckpt):
            return jsonify({"ok": True, "has_resumable": False, "checkpoint": None})

        active_sess = _sessions.get(sid)
        running_now = bool(active_sess and not active_sess.get("done"))
        if running_now:
            return jsonify({"ok": True, "has_resumable": False, "checkpoint": None, "running_now": True})

        # Suppress redundant Resume banner when chat already owns an active Action Plan card
        try:
            from hecos.core.action_plans import ACTIVE_PLAN_STATUSES, get_action_plan_manager

            active_plan = get_action_plan_manager().resolve_plan(source_id=sid)
            if active_plan and str(active_plan.get("status") or "").lower() in ACTIVE_PLAN_STATUSES:
                return jsonify({
                    "ok": True,
                    "has_resumable": False,
                    "checkpoint": None,
                    "suppressed_by_plan": active_plan.get("plan_id"),
                })
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "has_resumable": True,
            "checkpoint": _format_checkpoint_summary(ckpt, running_now=False),
        })

    @app.route("/api/agent/checkpoints/dismiss", methods=["POST"])
    def api_dismiss_agent_checkpoint():
        body = request.get_json(silent=True) or {}
        sid = _resolve_sid(body.get("session_id", ""))
        if not sid:
            return jsonify({"ok": False, "error": "Missing session_id"}), 400
        mark_checkpoint_status(sid, "dismissed", reason="dismissed by user")
        return jsonify({"ok": True, "session_id": sid})

    @app.route("/api/agent/checkpoints/resume", methods=["POST"])
    def api_resume_agent_checkpoint():
        from flask_login import current_user
        from hecos.memory.brain_interface import get_history
        from hecos.modules.web_ui.routes_chat_inference import (
            _run_inference,
            _sessions,
            _sessions_lock,
        )

        body = request.get_json(silent=True) or {}
        sid = _resolve_sid(body.get("session_id", ""))
        tab_id = str(body.get("tab_id") or "")
        if not sid:
            return jsonify({"ok": False, "error": "Missing session_id"}), 400

        ckpt = load_checkpoint(sid)
        if not is_resumable_checkpoint(ckpt):
            return jsonify({"ok": False, "error": "No resumable checkpoint found for this session."}), 404

        with _sessions_lock:
            from hecos.core.agent.turn_control import register_turn
            from hecos.modules.web_ui.server import get_state_manager

            existing = _sessions.get(sid)
            if existing and not existing.get("done") and not (
                existing.get("cancel_event") is not None and existing["cancel_event"].is_set()
            ):
                return jsonify({"ok": False, "error": "Task is already running in this session."}), 409

            turn_id, cancel_event = register_turn(sid)
            sm = get_state_manager()
            if sm:
                sm.webui_stop_requested = False

            uid = current_user.username if current_user.is_authenticated else "admin"
            urole = current_user.role if current_user.is_authenticated else "admin"
            raw_hist = get_history(user_id=uid, session_id=sid)
            hist_msgs = [
                {"role": "assistant" if row[0] == "ai" else row[0], "content": row[1]}
                for row in (raw_hist or [])
                if len(row) >= 2
            ]
            sess = {
                "queue": queue.Queue(),
                "history": hist_msgs,
                "done": False,
                "user_id": uid,
                "turn_id": turn_id,
                "cancel_event": cancel_event,
            }
            _sessions[sid] = sess

        user_text = str(ckpt.get("user_text") or "")
        threading.Thread(
            target=_run_inference,
            args=(sess, sid, user_text, hist_msgs, cfg_mgr, None, uid, urole, tab_id),
            kwargs={"resume_checkpoint": ckpt},
            daemon=True,
        ).start()
        logger.info(f"[AgentResume] Resuming checkpoint sid={sid[:8]} from step {ckpt.get('iteration', 0)}")
        return jsonify({"ok": True, "session_id": sid, "step": int(ckpt.get("iteration") or 0)})
