"""
hecos/modules/web_ui/action_plans/routes.py
HTTP endpoints for Core Action Plans config, live monitoring, human-in-the-loop approval,
and unified Agent/Flow checkpoint management in Central Hub -> SISTEMA.
"""

from __future__ import annotations

import os
from flask import Response, jsonify, make_response, render_template, request

from hecos.core.action_plans import (
    cleanup_expired_flow_checkpoints,
    cleanup_expired_plans,
    delete_flow_checkpoint,
    get_action_plan_manager,
    get_action_plans_config,
    list_flow_checkpoints,
    resolve_media_plans_dir,
    save_action_plans_config,
    sync_all_plans_to_media_dir,
)
from hecos.core.agent.checkpointing import (
    cleanup_expired_checkpoints,
    delete_checkpoint,
    list_checkpoints,
)


def init_action_plans_routes(app, cfg_mgr, logger) -> None:
    """Register /api/action-plans* and /action-plan-viewer endpoints on the WebUI Flask app."""
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            sync_all_plans_to_media_dir()
        except Exception as _sync_err:
            logger.debug(f"[ActionPlans] Initial media mirror sync skipped: {_sync_err}")

    @app.route("/action-plan-viewer", methods=["GET"])
    def action_plan_viewer_page():
        plan_id = (request.args.get("plan_id") or "").strip()
        sid = (request.args.get("sid") or "").strip()
        translations = {}
        try:
            from hecos.core.i18n.translator import get_translator
            translations = get_translator().get_translations() or {}
        except Exception:
            translations = {}

        ver_tag = ""
        try:
            ver_tag = str(app.jinja_env.globals.get("version") or "")
            if not ver_tag:
                from hecos.core.system.version import get_version
                ver_tag = str(get_version() or "1")
        except Exception:
            ver_tag = "1"

        zcfg = dict(getattr(cfg_mgr, "config", {}) or {})
        resp = make_response(render_template(
            "action_plan_viewer.html",
            zconfig=zcfg,
            translations=translations,
            version=ver_tag,
            plan_id=plan_id,
            sid=sid,
        ))
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        return resp

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
            "media_plans_dir": resolve_media_plans_dir(),
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

    @app.route("/api/action-plans/<plan_id>/revise", methods=["POST"])
    def api_revise_action_plan(plan_id: str):
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "Invalid JSON object"}), 400
        mgr = get_action_plan_manager()
        existing = mgr.get_plan(plan_id=plan_id)
        if not existing:
            return jsonify({"ok": False, "error": "Plan not found"}), 404
        res = mgr.revise_plan(
            plan_id=plan_id,
            title=body.get("title") if "title" in body else None,
            goal=body.get("goal") if "goal" in body else None,
            plan_markdown=body.get("plan_markdown") if "plan_markdown" in body else None,
            steps=body.get("steps") if "steps" in body else None,
            verification_plan=body.get("verification_plan") if "verification_plan" in body else None,
            revision_note=str(body.get("revision_note") or "Edited directly by user in Plan Viewer"),
            keep_awaiting_approval=bool(body.get("keep_awaiting_approval", existing.get("status") in ("awaiting_approval", "draft"))),
        )
        return jsonify(res), 200

    @app.route("/api/action-plans/<plan_id>/steps/<int:step_index>/toggle", methods=["POST"])
    def api_toggle_action_plan_step(plan_id: str, step_index: int):
        """Manually toggle a plan step between 'done' and 'pending' (or set an explicit status)."""
        body = request.get_json(silent=True) or {}
        mgr = get_action_plan_manager()
        res = mgr.toggle_step_manual(
            plan_id=plan_id,
            step_ref=step_index,
            status=str(body.get("status") or "").strip().lower(),
            notes=str(body.get("notes") or ""),
        )
        if not res.get("ok"):
            code = 404 if "not found" in str(res.get("error") or "").lower() else 400
            return jsonify(res), code
        return jsonify(res), 200

    @app.route("/api/action-plans/<plan_id>/reject", methods=["POST"])
    def api_reject_action_plan(plan_id: str):
        body = request.get_json(silent=True) or {}
        reason = str(body.get("reason") or "cancelled by user")
        res = get_action_plan_manager().reject_plan(plan_id, reason=reason)
        status_code = 200 if res.get("ok") else 404
        return jsonify(res), status_code

    def _default_plans_initialdir(requested: str = "") -> str:
        clean = str(requested or "").strip()
        if clean and os.path.isdir(clean):
            return clean
        try:
            plans_dir = resolve_media_plans_dir()
            if plans_dir and os.path.isdir(plans_dir):
                return plans_dir
        except Exception:
            pass
        try:
            from hecos.core.constants import MEDIA_DIR
            ws_dir = os.path.join(MEDIA_DIR, "workspace")
            if os.path.isdir(ws_dir):
                return ws_dir
            if os.path.isdir(MEDIA_DIR):
                return MEDIA_DIR
        except Exception:
            pass
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        return docs if os.path.isdir(docs) else os.path.expanduser("~")

    @app.route("/api/action-plans/open-folder", methods=["GET", "POST"])
    def api_open_action_plans_folder():
        """Sync and open hecos/media/action_plans in the native OS file manager."""
        try:
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                sync_all_plans_to_media_dir()
            folder = resolve_media_plans_dir()
            from hecos.core.system.os_adapter import OSAdapter
            details = OSAdapter.open_path_detailed(folder)
            if details.get("ok"):
                return jsonify({"ok": True, "path": folder, "details": details})
            return jsonify({"ok": False, "path": folder, "error": details.get("error") or "Failed to open folder"}), 500
        except Exception as exc:
            logger.error(f"[ActionPlans] open-folder error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/action-plans/<plan_id>/export", methods=["GET"])
    def api_export_action_plan(plan_id: str):
        fmt = (request.args.get("format") or "md").strip().lower()
        inline = (request.args.get("inline") or "").strip().lower() in ("1", "true", "yes")
        res = get_action_plan_manager().export_plan(plan_id, fmt=fmt)
        if not res.get("ok"):
            return jsonify(res), 404
        if inline:
            return jsonify(res), 200
        return Response(
            res["content"].encode("utf-8"),
            status=200,
            mimetype=res["mime"],
            headers={
                "Content-Disposition": f'attachment; filename="{res["filename"]}"',
                "Cache-Control": "no-store",
            },
        )

    @app.route("/api/action-plans/<plan_id>/export-native", methods=["POST"])
    def api_export_action_plan_native(plan_id: str):
        from hecos.core.action_plans.io_codec import (
            format_from_filename,
            normalize_export_format,
            suggest_plan_filename,
        )
        from hecos.modules.web_ui.routes_explorer import pick_native_os_path

        body = request.get_json(silent=True) or {}
        req_fmt = normalize_export_format(body.get("format") or "md")
        mgr = get_action_plan_manager()
        plan = mgr.get_plan(plan_id=plan_id)
        if not plan:
            return jsonify({"ok": False, "error": "Plan not found"}), 404

        default_name = suggest_plan_filename(plan, req_fmt)
        all_filters = {
            "md": ["Markdown Blueprint", "*.md"],
            "html": ["Interactive HTML Report (Printable)", "*.html *.htm"],
            "yaml": ["Structured YAML Plan", "*.yaml *.yml"],
            "json": ["Hecos Action Plan JSON", "*.hecos-plan.json *.json"],
        }
        ordered_keys = [req_fmt] + [k for k in ("md", "html", "yaml", "json") if k != req_fmt]
        filetypes = [all_filters[k] for k in ordered_keys] + [["All Files", "*.*"]]

        init_dir = _default_plans_initialdir(body.get("initialdir", ""))
        try:
            chosen_path = pick_native_os_path(
                mode="save",
                title=str(body.get("title") or "Hecos — Export Action Plan"),
                initialdir=init_dir,
                filetypes=filetypes,
                default_name=default_name,
                default_ext=req_fmt,
            )
        except Exception as exc:
            logger.error(f"[ActionPlans] Native export dialog failed: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

        if not chosen_path:
            return jsonify({"ok": True, "cancelled": True}), 200

        eff_fmt = format_from_filename(chosen_path, fallback=req_fmt)
        exported = mgr.export_plan(plan_id, fmt=eff_fmt)
        if not exported.get("ok"):
            return jsonify(exported), 404

        try:
            parent = os.path.dirname(os.path.abspath(chosen_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            data_bytes = exported["content"].encode("utf-8")
            with open(chosen_path, "wb") as fh:
                fh.write(data_bytes)
        except Exception as exc:
            logger.error(f"[ActionPlans] Failed writing exported plan to {chosen_path}: {exc}")
            return jsonify({"ok": False, "error": f"Failed to write file: {exc}"}), 500

        logger.info(f"[ActionPlans] Exported {plan_id} ({eff_fmt}) -> {chosen_path}")
        return jsonify({
            "ok": True,
            "cancelled": False,
            "plan_id": plan_id,
            "path": os.path.abspath(chosen_path),
            "directory": os.path.dirname(os.path.abspath(chosen_path)),
            "filename": os.path.basename(chosen_path),
            "format": eff_fmt,
            "bytes": len(data_bytes),
        }), 200

    @app.route("/api/action-plans/import", methods=["POST"])
    def api_import_action_plan():
        mgr = get_action_plan_manager()
        if request.files and "file" in request.files:
            up = request.files["file"]
            raw_bytes = up.read()
            try:
                content = raw_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = raw_bytes.decode("latin-1", errors="replace")
            filename = str(up.filename or "imported_plan.md")
            source_id = str(request.form.get("source_id") or "").strip()
            reset_progress = str(request.form.get("reset_progress") or "").lower() in ("1", "true", "yes")
        else:
            body = request.get_json(silent=True) or {}
            if not isinstance(body, dict):
                return jsonify({"ok": False, "error": "Invalid JSON object"}), 400
            content = body.get("content")
            filename = str(body.get("filename") or "").strip()
            source_id = str(body.get("source_id") or "").strip()
            reset_progress = bool(body.get("reset_progress", False))

        res = mgr.import_plan(
            content=content,
            filename=filename,
            source_id=source_id,
            reset_progress=reset_progress,
        )
        return jsonify(res), (200 if res.get("ok") else 400)

    @app.route("/api/action-plans/import-native", methods=["POST"])
    def api_import_action_plan_native():
        from hecos.modules.web_ui.routes_explorer import pick_native_os_path

        body = request.get_json(silent=True) or {}
        source_id = str(body.get("source_id") or "").strip()
        reset_progress = bool(body.get("reset_progress", False))
        init_dir = _default_plans_initialdir(body.get("initialdir", ""))

        try:
            chosen_path = pick_native_os_path(
                mode="open",
                title=str(body.get("title") or "Hecos — Import Action Plan"),
                initialdir=init_dir,
                filetypes=[
                    ["Hecos Action Plans", "*.md *.html *.htm *.yaml *.yml *.hecos-plan.json *.json"],
                    ["Markdown Blueprint", "*.md"],
                    ["Interactive HTML Report", "*.html *.htm"],
                    ["Structured YAML Plan", "*.yaml *.yml"],
                    ["Hecos Action Plan JSON", "*.hecos-plan.json *.json"],
                    ["All Files", "*.*"],
                ],
            )
        except Exception as exc:
            logger.error(f"[ActionPlans] Native import dialog failed: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

        if not chosen_path:
            return jsonify({"ok": True, "cancelled": True}), 200

        res = get_action_plan_manager().import_plan(
            file_path=chosen_path,
            source_id=source_id,
            reset_progress=reset_progress,
        )
        if not res.get("ok"):
            return jsonify(res), 400

        abs_path = os.path.abspath(chosen_path)
        logger.info(f"[ActionPlans] Imported plan {res['plan']['plan_id']} <- {abs_path}")
        return jsonify({
            "ok": True,
            "cancelled": False,
            "path": abs_path,
            "directory": os.path.dirname(abs_path),
            "filename": os.path.basename(abs_path),
            "plan": res["plan"],
        }), 200

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
