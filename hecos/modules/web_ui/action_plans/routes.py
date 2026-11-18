"""
hecos/modules/web_ui/action_plans/routes.py
HTTP endpoints for Core Action Plans config, live monitoring, human-in-the-loop approval,
and unified Agent/Flow checkpoint management in Central Hub -> SISTEMA.
"""

from __future__ import annotations

from flask import jsonify, request

from hecos.core.action_plans import (
    cleanup_expired_flow_checkpoints,
    cleanup_expired_plans,
    delete_flow_checkpoint,
    get_action_plan_manager,
    get_action_plans_config,
    list_flow_checkpoints,
    save_action_plans_config,
)
from hecos.core.agent.checkpointing import (
    cleanup_expired_checkpoints,
    delete_checkpoint,
    list_checkpoints,
)


def init_action_plans_routes(app, cfg_mgr, logger) -> None:
    """Register /api/action-plans* endpoints on the WebUI Flask app."""

    @app.route("/api/action-plans/config", methods=["GET"])
    def api_get_action_plans_config():
        return jsonify({"ok": True, "config": get_action_plans_config(cfg_mgr=cfg_mgr)})

    @app.route("/api/action-plans/config", methods=["POST"])
    def api_post_action_plans_config():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "Invalid JSON object"}), 400
        saved = save_action_plans_config(body, cfg_mgr=cfg_mgr)
        logger.info(f"[ActionPlans] Configuration updated: plan_mode={saved.get('plan_mode')}")
        return jsonify({"ok": True, "config": saved})

    @app.route("/api/action-plans", methods=["GET"])
    def api_list_action_plans():
        scope = (request.args.get("scope") or "").strip() or None
        status = (request.args.get("status") or "").strip() or None
        source_id = (request.args.get("source_id") or "").strip() or None
        mgr = get_action_plan_manager()

        if source_id:
            active = mgr.get_plan(source_id=source_id)
            return jsonify({"ok": True, "active_plan": active})

        plans = mgr.list_all(scope=scope, status=status, limit=40)
        agent_ckpts = list_checkpoints(limit=30)
        flow_ckpts = list_flow_checkpoints(only_resumable=False, limit=30)
        return jsonify({
            "ok": True,
            "config": get_action_plans_config(cfg_mgr=cfg_mgr),
            "plans": plans,
            "agent_checkpoints": [
                {
                    "session_id": c.get("session_id"),
                    "status": c.get("status"),
                    "reason": c.get("reason", ""),
                    "iteration": int(c.get("iteration") or 0),
                    "max_iterations": int(c.get("max_iterations") or 25),
                    "model_label": c.get("model_label", ""),
                    "plan_id": c.get("plan_id", ""),
                    "user_preview": str(c.get("user_text") or "")[:120],
                    "updated_at": float(c.get("updated_at") or 0),
                }
                for c in agent_ckpts
            ],
            "flow_checkpoints": [
                {
                    "run_id": f.get("run_id"),
                    "flow_id": f.get("flow_id"),
                    "flow_name": f.get("flow_name"),
                    "status": f.get("status"),
                    "error_msg": f.get("error_msg", ""),
                    "completed_count": len(f.get("completed") or []),
                    "total_steps": int(f.get("total_steps") or 0),
                    "updated_at": float(f.get("updated_at") or 0),
                }
                for f in flow_ckpts
            ],
        })

    @app.route("/api/action-plans/<plan_id>", methods=["GET"])
    def api_get_action_plan(plan_id: str):
        plan = get_action_plan_manager().get_plan(plan_id=plan_id)
        if not plan:
            return jsonify({"ok": False, "error": "Plan not found"}), 404
        return jsonify({"ok": True, "plan": plan})

    @app.route("/api/action-plans/<plan_id>/approve", methods=["POST"])
    def api_approve_action_plan(plan_id: str):
        body = request.get_json(silent=True) or {}
        edited_steps = body.get("steps")
        res = get_action_plan_manager().approve_plan(plan_id, edited_steps=edited_steps)
        status_code = 200 if res.get("ok") else 404
        return jsonify(res), status_code

    @app.route("/api/action-plans/<plan_id>/reject", methods=["POST"])
    def api_reject_action_plan(plan_id: str):
        body = request.get_json(silent=True) or {}
        reason = str(body.get("reason") or "cancelled by user")
        res = get_action_plan_manager().reject_plan(plan_id, reason=reason)
        status_code = 200 if res.get("ok") else 404
        return jsonify(res), status_code

    @app.route("/api/action-plans/<plan_id>", methods=["DELETE"])
    def api_delete_action_plan(plan_id: str):
        ok = get_action_plan_manager().remove_plan(plan_id)
        return jsonify({"ok": ok, "plan_id": plan_id})

    @app.route("/api/action-plans/checkpoints/purge", methods=["POST"])
    def api_purge_checkpoints():
        body = request.get_json(silent=True) or {}
        target_type = str(body.get("type") or "expired").lower()
        target_id = str(body.get("id") or "").strip()

        if target_type == "agent" and target_id:
            return jsonify({"ok": delete_checkpoint(target_id), "removed": 1})
        if target_type == "flow" and target_id:
            return jsonify({"ok": delete_flow_checkpoint(target_id), "removed": 1})

        cfg = get_action_plans_config(cfg_mgr=cfg_mgr)
        days = int(body.get("retention_days") if body.get("retention_days") is not None else cfg.get("retention_days", 14))
        removed_plans = cleanup_expired_plans(days)
        removed_agent = cleanup_expired_checkpoints(days)
        removed_flows = cleanup_expired_flow_checkpoints(days)
        return jsonify({
            "ok": True,
            "retention_days": days,
            "removed": {
                "plans": removed_plans,
                "agent_checkpoints": removed_agent,
                "flow_checkpoints": removed_flows,
            },
        })
