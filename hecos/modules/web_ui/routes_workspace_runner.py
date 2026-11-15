"""
MODULE: Web UI Workspace Runner Routes
DESCRIPTION: REST endpoints to catalog, run, test, stream logs, and stop
             scripts/apps generated inside C:\\Hecos\\hecos\\media\\workspace.
"""

from __future__ import annotations

import os
import re
from flask import jsonify, request

from hecos.modules.executor.main import tools as executor_tools
from hecos.modules.executor.process_runner import (
    get_process_registry,
    list_workspace_projects,
    run_smart,
)

_RUN_ID_RE = re.compile(r"^run_\d+_[a-f0-9]+$")


def init_workspace_runner_routes(app, cfg_mgr, logger):
    """Register /api/workspace/* endpoints for the chat cards and Workspace Runner modal."""

    def _is_ui_execution_enabled() -> bool:
        try:
            if cfg_mgr:
                return bool(cfg_mgr.get_plugin_config("EXECUTOR", "allow_ui_script_execution", True))
        except Exception:
            pass
        return True

    def _default_timeout() -> int:
        try:
            if cfg_mgr:
                return int(cfg_mgr.get_plugin_config("EXECUTOR", "default_run_timeout_seconds", 30))
        except (TypeError, ValueError):
            pass
        return 30

    def _normalize_client_path(raw_path: str) -> str:
        clean = (raw_path or "").strip()
        if clean.startswith("file:///"):
            clean = clean[8:]
        elif clean.startswith("file://"):
            clean = clean[7:]
        return clean

    @app.route("/api/workspace/projects", methods=["GET"])
    def workspace_list_projects():
        try:
            ws_dir = executor_tools._resolve_workspace_dir()
            sb_dir = executor_tools._resolve_sandbox_dir()
            os.makedirs(ws_dir, exist_ok=True)
            projects = list_workspace_projects(ws_dir)
            runs = get_process_registry().list_runs()
            active_count = sum(1 for r in runs if r.get("status") == "running")
            return jsonify({
                "ok": True,
                "workspace_dir": ws_dir,
                "sandbox_dir": sb_dir,
                "projects": projects,
                "active_count": active_count,
                "ui_execution_enabled": _is_ui_execution_enabled(),
            })
        except Exception as exc:
            logger.error(f"[WorkspaceRunner] Failed to list projects: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/workspace/runs", methods=["GET"])
    def workspace_list_runs():
        try:
            runs = get_process_registry().list_runs()
            active_count = sum(1 for r in runs if r.get("status") == "running")
            return jsonify({"ok": True, "runs": runs, "active_count": active_count})
        except Exception as exc:
            logger.error(f"[WorkspaceRunner] Failed to list runs: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/workspace/run", methods=["POST"])
    def workspace_run_target():
        if not _is_ui_execution_enabled():
            return jsonify({
                "ok": False,
                "error": "UI script execution is disabled in EXECUTOR plugin settings.",
            }), 403

        data = request.get_json(silent=True) or {}
        raw_path = _normalize_client_path(data.get("path", ""))
        mode = str(data.get("mode", "auto") or "auto").strip().lower()
        args = str(data.get("args", "") or "")
        wait_seconds = data.get("wait_seconds", 1.5)
        try:
            wait_val = max(0.2, min(float(wait_seconds), 8.0))
        except (TypeError, ValueError):
            wait_val = 1.5

        if mode not in {"auto", "script", "test", "app"}:
            return jsonify({"ok": False, "error": f"Unsupported mode '{mode}'."}), 400
        if not raw_path:
            return jsonify({"ok": False, "error": "Missing target path."}), 400

        ws_dir = executor_tools._resolve_workspace_dir()
        sb_dir = executor_tools._resolve_sandbox_dir()
        res = run_smart(
            raw_path,
            mode=mode,
            args=args,
            workspace_dir=ws_dir,
            sandbox_dir=sb_dir,
            timeout_seconds=_default_timeout(),
            wait_seconds=wait_val,
            strict_workspace_only=True,
        )
        status_code = 403 if str(res.get("error", "")).lower().startswith("access denied") else 200
        return jsonify(res), status_code

    @app.route("/api/workspace/runs/<run_id>/logs", methods=["GET"])
    def workspace_run_logs(run_id: str):
        if not _RUN_ID_RE.match(run_id or ""):
            return jsonify({"ok": False, "error": "Invalid run_id."}), 400
        try:
            offset = int(request.args.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0
        try:
            tail_lines = int(request.args.get("tail_lines", 0))
        except (TypeError, ValueError):
            tail_lines = 0

        res = get_process_registry().get_logs(run_id, offset=offset, tail_lines=tail_lines)
        return jsonify(res), (200 if res.get("ok") else 404)

    @app.route("/api/workspace/runs/<run_id>/stop", methods=["POST"])
    def workspace_stop_run(run_id: str):
        if not _RUN_ID_RE.match(run_id or ""):
            return jsonify({"ok": False, "error": "Invalid run_id."}), 400
        res = get_process_registry().stop_run(run_id)
        return jsonify(res), (200 if res.get("ok") else 404)
