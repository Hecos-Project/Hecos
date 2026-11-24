"""
hecos/modules/executor/cli_bridge/routes_cli_bridge.py
Modular Flask routes for Hecos CLI Bridge:
- Live Action Feed (`/api/workspace/cli/actions`, `/drive/api/editor/cli/actions`)
- Native Terminal & Interactive Aider Launcher (`/api/workspace/cli/open`, `/drive/api/editor/cli/open`)
- Direct In-IDE Streaming Aider Runner (`/api/workspace/cli/aider_direct`, `/drive/api/editor/cli/aider_direct`)
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List

from flask import jsonify, request
from flask_login import login_required

from ..process_runner import resolve_authorized_target
from .action_feed import clear_action_events, get_action_events
from .direct_aider_runner import (
    get_direct_aider_task,
    start_direct_aider_task,
    stop_direct_aider_task,
)
from .terminal_launcher import launch_native_terminal


def _normalize_client_path(raw_path: str) -> str:
    clean = str(raw_path or "").strip()
    if clean.lower().startswith("file:///"):
        clean = clean[8:]
    elif clean.lower().startswith("file://"):
        clean = clean[7:]
    if os.name == "nt":
        clean = clean.replace("/", "\\")
    return clean


def _parse_files_list(raw_files: Any) -> List[str]:
    if isinstance(raw_files, list):
        return [str(x).strip() for x in raw_files if str(x).strip()]
    if isinstance(raw_files, str) and raw_files.strip():
        return [x.strip() for x in raw_files.split(",") if x.strip()]
    return []


def register_cli_bridge_routes(
    app: Any,
    executor_tools: Any,
    is_ui_execution_enabled: Callable[[], bool],
    logger: Any,
) -> None:
    """Register `/api/workspace/cli/*` endpoints on the main WebUI Flask app."""

    @app.route("/api/workspace/cli/actions", methods=["GET"])
    def workspace_cli_actions():
        since_seq = request.args.get("since_seq", 0, type=int)
        limit = request.args.get("limit", 120, type=int)
        return jsonify(get_action_events(since_seq=since_seq, limit=limit))

    @app.route("/api/workspace/cli/actions/clear", methods=["POST"])
    def workspace_cli_actions_clear():
        return jsonify(clear_action_events())

    @app.route("/api/workspace/cli/open", methods=["POST"])
    def workspace_cli_open():
        if not is_ui_execution_enabled():
            return jsonify({
                "ok": False,
                "error": "UI execution is disabled in EXECUTOR plugin settings.",
            }), 403

        data = request.get_json(silent=True) or {}
        mode = str(data.get("mode") or "shell").strip().lower()
        if mode not in {"shell", "aider", "trace"}:
            return jsonify({"ok": False, "error": f"Unsupported CLI mode '{mode}'."}), 400

        ws_dir = executor_tools._resolve_workspace_dir()
        raw_path = _normalize_client_path(data.get("path", ""))
        target_path = ws_dir
        if raw_path:
            resolved, err = resolve_authorized_target(raw_path, ws_dir, strict_workspace_only=False)
            if err or not resolved:
                return jsonify({"ok": False, "error": err or "Invalid path."}), 403
            target_path = resolved

        files = _parse_files_list(data.get("files"))
        model = str(data.get("model") or "").strip()
        dry_run = bool(data.get("dry_run", False))

        res = launch_native_terminal(
            mode=mode,
            target_path=target_path,
            files=files,
            model=model,
            workspace_dir=ws_dir,
            dry_run=dry_run,
        )
        logger.info(f"[CLI_BRIDGE] Open mode={mode} path={target_path} ok={res.get('ok')}")
        return jsonify(res), (200 if res.get("ok") else 400)

    @app.route("/api/workspace/cli/aider_direct", methods=["POST"])
    def workspace_cli_aider_direct():
        if not is_ui_execution_enabled():
            return jsonify({
                "ok": False,
                "error": "UI execution is disabled in EXECUTOR plugin settings.",
            }), 403

        data = request.get_json(silent=True) or {}
        instruction = str(data.get("instruction") or data.get("prompt") or "").strip()
        if not instruction:
            return jsonify({"ok": False, "error": "Missing Aider instruction."}), 400

        ws_dir = executor_tools._resolve_workspace_dir()
        raw_path = _normalize_client_path(data.get("path", ""))
        target_path = ws_dir
        if raw_path:
            resolved, err = resolve_authorized_target(raw_path, ws_dir, strict_workspace_only=False)
            if err or not resolved:
                return jsonify({"ok": False, "error": err or "Invalid path."}), 403
            target_path = resolved

        files_arg = data.get("files", "")
        if isinstance(files_arg, list):
            files_arg = ",".join(str(x) for x in files_arg if x)
        model = str(data.get("model") or "").strip()

        res = start_direct_aider_task(
            target_path=target_path,
            instruction=instruction,
            files=str(files_arg or ""),
            model=model,
            workspace_dir=ws_dir,
        )
        return jsonify(res), (200 if res.get("ok") else 400)

    @app.route("/api/workspace/cli/aider_direct/<task_id>", methods=["GET"])
    def workspace_cli_aider_direct_status(task_id: str):
        offset = request.args.get("offset", 0, type=int)
        res = get_direct_aider_task(task_id, offset=offset)
        return jsonify(res), (200 if res.get("ok") else 404)

    @app.route("/api/workspace/cli/aider_direct/<task_id>/stop", methods=["POST"])
    def workspace_cli_aider_direct_stop(task_id: str):
        res = stop_direct_aider_task(task_id)
        return jsonify(res), (200 if res.get("ok") else 404)


def register_ide_cli_routes(bp: Any, ctx: Dict[str, Any]) -> None:
    """Register `/drive/api/editor/cli/*` endpoints on the Drive/Monaco IDE Blueprint."""
    _get_drive_root = ctx["get_drive_root"]
    _safe_path = ctx["safe_path"]
    logger = ctx["logger"]

    @bp.route("/drive/api/editor/cli/actions", methods=["GET"])
    @login_required
    def drive_editor_cli_actions():
        since_seq = request.args.get("since_seq", 0, type=int)
        limit = request.args.get("limit", 120, type=int)
        return jsonify(get_action_events(since_seq=since_seq, limit=limit))

    @bp.route("/drive/api/editor/cli/actions/clear", methods=["POST"])
    @login_required
    def drive_editor_cli_actions_clear():
        return jsonify(clear_action_events())

    @bp.route("/drive/api/editor/cli/open", methods=["POST"])
    @login_required
    def drive_editor_cli_open():
        data = request.get_json(silent=True) or {}
        mode = str(data.get("mode") or "shell").strip().lower()
        if mode not in {"shell", "aider", "trace"}:
            return jsonify({"ok": False, "error": f"Unsupported CLI mode '{mode}'."}), 400

        root = _get_drive_root()
        raw_path = str(data.get("path") or "").strip()
        target = _safe_path(root, raw_path) if raw_path else root
        if target is None:
            return jsonify({"ok": False, "error": "Path not allowed."}), 403

        files_raw = _parse_files_list(data.get("files"))
        safe_files: List[str] = []
        for f in files_raw:
            sf = _safe_path(root, f)
            if sf and os.path.isfile(sf):
                safe_files.append(sf)

        res = launch_native_terminal(
            mode=mode,
            target_path=target,
            files=safe_files,
            model=str(data.get("model") or "").strip(),
            workspace_dir=root,
            dry_run=bool(data.get("dry_run", False)),
        )
        logger.info(f"[EDITOR_CLI] Open mode={mode} target={target} ok={res.get('ok')}")
        return jsonify(res), (200 if res.get("ok") else 400)

    @bp.route("/drive/api/editor/cli/aider_direct", methods=["POST"])
    @login_required
    def drive_editor_cli_aider_direct():
        data = request.get_json(silent=True) or {}
        instruction = str(data.get("instruction") or data.get("prompt") or "").strip()
        if not instruction:
            return jsonify({"ok": False, "error": "Missing Aider instruction."}), 400

        root = _get_drive_root()
        raw_path = str(data.get("path") or "").strip()
        target = _safe_path(root, raw_path) if raw_path else root
        if target is None:
            return jsonify({"ok": False, "error": "Path not allowed."}), 403

        files_raw = _parse_files_list(data.get("files"))
        safe_files: List[str] = []
        for f in files_raw:
            sf = _safe_path(root, f)
            if sf and os.path.isfile(sf):
                safe_files.append(sf)

        res = start_direct_aider_task(
            target_path=target,
            instruction=instruction,
            files=",".join(safe_files),
            model=str(data.get("model") or "").strip(),
            workspace_dir=root,
        )
        return jsonify(res), (200 if res.get("ok") else 400)

    @bp.route("/drive/api/editor/cli/aider_direct/<task_id>", methods=["GET"])
    @login_required
    def drive_editor_cli_aider_direct_status(task_id: str):
        offset = request.args.get("offset", 0, type=int)
        res = get_direct_aider_task(task_id, offset=offset)
        return jsonify(res), (200 if res.get("ok") else 404)

    @bp.route("/drive/api/editor/cli/aider_direct/<task_id>/stop", methods=["POST"])
    @login_required
    def drive_editor_cli_aider_direct_stop(task_id: str):
        res = stop_direct_aider_task(task_id)
        return jsonify(res), (200 if res.get("ok") else 404)
