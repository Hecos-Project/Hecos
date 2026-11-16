"""
MODULE: Web UI Workspace Runner Routes
DESCRIPTION: REST endpoints to catalog, run, test, stream logs, and stop
             scripts/apps generated inside C:\\Hecos\\hecos\\media\\workspace.
"""

from __future__ import annotations

import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from flask import Response, jsonify, render_template, request

from hecos.modules.executor.main import tools as executor_tools
from hecos.modules.executor.process_runner import (
    _is_loopback_http_url,
    get_process_registry,
    list_workspace_projects,
    resolve_authorized_target,
    run_smart,
)

_RUN_ID_RE = re.compile(r"^run_\d+_[a-f0-9]+$")
_IGNORE_SIG_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".pytest_cache"}
_BACKEND_ENTRY_CANDIDATES = ("app.py", "main.py", "server.py", "run.py")


def find_matching_running_app(abs_target: str) -> dict | None:
    """Return the running ManagedProcessRegistry record whose directory owns abs_target."""
    if not abs_target:
        return None
    target_dir = abs_target if os.path.isdir(abs_target) else os.path.dirname(abs_target)
    norm_target_dir = os.path.normcase(os.path.abspath(target_dir))
    for r in get_process_registry().list_runs():
        if r.get("status") != "running":
            continue
        urls = r.get("detected_urls") or []
        if not urls or not _is_loopback_http_url(urls[0]):
            continue
        r_path = r.get("path") or ""
        r_dir = os.path.normcase(os.path.abspath(os.path.dirname(r_path))) if r_path else ""
        if r_dir and (
            norm_target_dir == r_dir
            or norm_target_dir.startswith(r_dir + os.sep)
            or r_dir.startswith(norm_target_dir + os.sep)
        ):
            return r
    return None


def _inject_proxy_shim(html_bytes: bytes, run_id: str, app_dir: str = "") -> bytes:
    from hecos.modules.web_ui.routes_chat_media import rewrite_html_local_media_refs

    base_href = f"/api/workspace/preview_proxy/{run_id}/"
    prefix = f"/api/workspace/preview_proxy/{run_id}"
    shim = (
        f'<base href="{base_href}">'
        f'<script>(function(){{var P="{prefix}";'
        f'var rw=function(u){{if(typeof u==="string"&&u.startsWith("/")&&!u.startsWith("//")&&!u.startsWith(P)&&!u.startsWith("/api/local_file")&&!u.startsWith("/api/serve_html")&&!u.startsWith("/api/images")){{return P+u;}}return u;}};'
        f'var _f=window.fetch;if(_f){{window.fetch=function(i,n){{return _f(typeof i==="string"?rw(i):i,n);}};}}'
        f'var _o=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(m,u){{var a=Array.prototype.slice.call(arguments);if(typeof u==="string")a[1]=rw(u);return _o.apply(this,a);}};}})();</script>'
    )
    text = html_bytes.decode("utf-8", errors="replace")
    text = rewrite_html_local_media_refs(text, base_dir=app_dir, rewrite_relative=False)
    head_match = re.search(r"<head\b[^>]*>", text, re.IGNORECASE)
    if head_match:
        pos = head_match.end()
        out = text[:pos] + shim + text[pos:]
    else:
        out = shim + text
    return out.encode("utf-8")


def proxy_workspace_run_request(run_id: str, subpath: str = "") -> Response:
    """Proxy an HTTP request to an active loopback workspace app and rewrite HTML assets/APIs."""
    if not _RUN_ID_RE.match(run_id or ""):
        return Response('{"ok":false,"error":"Invalid run_id."}', status=400, mimetype="application/json")
    logs_res = get_process_registry().get_logs(run_id, offset=0, tail_lines=1)
    if not logs_res.get("ok"):
        return Response('{"ok":false,"error":"Unknown run_id."}', status=404, mimetype="application/json")
    urls = logs_res.get("detected_urls") or []
    if not urls or not _is_loopback_http_url(urls[0]):
        return Response('{"ok":false,"error":"Run has no loopback HTTP URL."}', status=404, mimetype="application/json")

    base_url = urls[0].rstrip("/") + "/"
    target_url = urljoin(base_url, subpath or "")
    qs = request.query_string.decode("utf-8", errors="ignore")
    if qs and not target_url.endswith("/") and subpath:
        target_url = f"{target_url}?{qs}"
    elif qs and not subpath and request.path.startswith("/api/workspace/preview_proxy"):
        target_url = f"{target_url}?{qs}"

    req_headers = {}
    ctype_in = request.headers.get("Content-Type")
    if ctype_in:
        req_headers["Content-Type"] = ctype_in
    body_data = request.get_data() if request.method in ("POST", "PUT", "PATCH") else None

    upstream_req = Request(target_url, data=body_data, headers=req_headers, method=request.method)
    try:
        with urlopen(upstream_req, timeout=8.0) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            ctype = (resp.headers.get("Content-Type") or "application/octet-stream")
            raw_body = resp.read()
    except HTTPError as herr:
        status = int(herr.code)
        ctype = (herr.headers.get("Content-Type") or "text/plain") if herr.headers else "text/plain"
        raw_body = herr.read()
    except URLError as uerr:
        return Response(f"Preview backend unreachable: {uerr.reason}", status=502, mimetype="text/plain")
    except Exception as exc:
        return Response(f"Preview proxy error: {exc}", status=502, mimetype="text/plain")

    app_dir = os.path.dirname(logs_res.get("path") or "") if logs_res.get("path") else ""
    if "text/html" in ctype.lower() and (not subpath or subpath.lower().endswith((".html", ".htm"))):
        raw_body = _inject_proxy_shim(raw_body, run_id, app_dir=app_dir)

    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    return Response(raw_body, status=status, mimetype=ctype.split(";")[0].strip(), headers=headers)


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

    @app.route("/workspace")
    @app.route("/workspace/")
    def standalone_workspace_page():
        """Render the standalone full-page Workspace Runner + Live Console + Aider workspace."""
        lm = getattr(app, "login_manager", None)
        if lm is not None:
            try:
                from flask_login import current_user

                if not current_user.is_authenticated:
                    return lm.unauthorized()
            except Exception:
                pass
        try:
            from hecos.core.i18n.translator import get_translator
            from hecos.core.utils.version import get_version_string

            translations = get_translator().get_translations()
            version = get_version_string()
        except Exception:
            translations = {}
            version = "dev"

        def _t(key: str, default: str | None = None) -> str:
            return translations.get(key) or default or key

        ws_dir = ""
        try:
            ws_dir = str(executor_tools._resolve_workspace_dir() or "").replace("\\", "/")
        except Exception:
            ws_dir = "C:/Hecos/hecos/media/workspace"
        logger.debug("[WORKSPACE_UI] Serving standalone /workspace page")
        return render_template(
            "workspace.html",
            zconfig=(cfg_mgr.config if cfg_mgr and hasattr(cfg_mgr, "config") else {}),
            translations=translations,
            version=version,
            t=_t,
            workspace_dir=ws_dir or "C:/Hecos/hecos/media/workspace",
        )

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
            logger.warning("[WORKSPACE_UI] Run blocked: UI execution disabled in settings.")
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

        logger.info(f"[WORKSPACE_UI] Run requested mode={mode} target={raw_path}")
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
        probe = res.get("http_probe")
        if isinstance(probe, dict) and not probe.get("ok") and res.get("path"):
            try:
                from hecos.modules.executor.dev_tools import inspect_web_project_issues
                res["web_diagnostics"] = inspect_web_project_issues(res["path"])
            except Exception:
                pass
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
        try:
            tail_bytes = int(request.args.get("tail_bytes", 0))
        except (TypeError, ValueError):
            tail_bytes = 0

        res = get_process_registry().get_logs(run_id, offset=offset, tail_lines=tail_lines, tail_bytes=tail_bytes)
        return jsonify(res), (200 if res.get("ok") else 404)

    @app.route("/api/workspace/runs/<run_id>/logs/raw", methods=["GET"])
    def workspace_run_logs_raw(run_id: str):
        if not _RUN_ID_RE.match(run_id or ""):
            return jsonify({"ok": False, "error": "Invalid run_id."}), 400
        info = get_process_registry().get_run_log_path(run_id)
        if not info:
            return jsonify({"ok": False, "error": f"Unknown run_id or missing log file: {run_id}"}), 404
        log_path, name = info
        try:
            with open(log_path, "rb") as fb:
                raw_bytes = fb.read()
        except OSError as exc:
            logger.error(f"[WORKSPACE_UI] Failed reading raw log {log_path}: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

        safe_name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", f"{name}_{run_id}.log")
        headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
        if request.args.get("download") in ("1", "true", "yes"):
            headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'
        logger.debug(f"[WORKSPACE_UI] Served raw log {run_id} ({len(raw_bytes)} bytes)")
        return Response(raw_bytes, mimetype="text/plain; charset=utf-8", headers=headers)

    @app.route("/api/workspace/runs/<run_id>/stop", methods=["POST"])
    def workspace_stop_run(run_id: str):
        if not _RUN_ID_RE.match(run_id or ""):
            return jsonify({"ok": False, "error": "Invalid run_id."}), 400
        logger.info(f"[WORKSPACE_UI] Stop requested run_id={run_id}")
        res = get_process_registry().stop_run(run_id)
        return jsonify(res), (200 if res.get("ok") else 404)

    @app.route("/api/workspace/aider/status", methods=["GET"])
    def workspace_aider_status():
        try:
            from hecos.modules.executor.aider_bridge import get_aider_status

            st = get_aider_status(check_version=True)
            return jsonify({"ok": True, **st})
        except Exception as exc:
            logger.error(f"[WorkspaceRunner] Aider status check failed: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/workspace/aider/install", methods=["POST"])
    def workspace_aider_install():
        if not _is_ui_execution_enabled():
            return jsonify({
                "ok": False,
                "error": "UI execution is disabled in EXECUTOR plugin settings.",
            }), 403
        try:
            from hecos.modules.executor.aider_bridge import install_or_update_aider

            res = install_or_update_aider(timeout_seconds=300)
            return jsonify(res), (200 if res.get("ok") else 500)
        except Exception as exc:
            logger.error(f"[WorkspaceRunner] Aider install/update failed: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    def _compute_folder_signature(target_file: str) -> str:
        base_dir = target_file if os.path.isdir(target_file) else os.path.dirname(target_file)
        if not base_dir or not os.path.isdir(base_dir):
            return "0:0:0"
        count = 0
        max_mtime = 0
        total_size = 0
        try:
            for root_p, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in _IGNORE_SIG_DIRS and not d.startswith(".")]
                for fname in files:
                    fpath = os.path.join(root_p, fname)
                    try:
                        st = os.stat(fpath)
                        count += 1
                        if st.st_mtime_ns > max_mtime:
                            max_mtime = st.st_mtime_ns
                        total_size += st.st_size
                    except OSError:
                        pass
                if count >= 200:
                    break
        except OSError:
            pass
        return f"{count}:{max_mtime}:{total_size}"

    def _find_backend_entry(target_dir: str) -> str:
        if not target_dir or not os.path.isdir(target_dir):
            return ""
        for cand in _BACKEND_ENTRY_CANDIDATES:
            full = os.path.join(target_dir, cand)
            if os.path.isfile(full):
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                        head = fh.read(4096).lower()
                    if any(k in head for k in ("flask(", "fastapi(", "streamlit", "aiohttp", "tornado", "http.server", "uvicorn.run", "app.run(")):
                        return full
                except OSError:
                    pass
        return ""

    @app.route("/api/workspace/preview_target", methods=["GET"])
    def workspace_preview_target():
        raw_path = _normalize_client_path(request.args.get("path", ""))
        if not raw_path:
            return jsonify({"ok": False, "error": "Missing path parameter."}), 400
        ws_dir = executor_tools._resolve_workspace_dir()
        abs_target, err = resolve_authorized_target(raw_path, ws_dir, strict_workspace_only=False)
        if err or not abs_target:
            return jsonify({"ok": False, "error": err or "Invalid path."}), 404

        target_dir = abs_target if os.path.isdir(abs_target) else os.path.dirname(abs_target)
        matched_run = find_matching_running_app(abs_target)
        backend_entry = _find_backend_entry(target_dir)
        run_id = matched_run["run_id"] if matched_run else ""
        app_url = (matched_run.get("detected_urls") or [""])[0] if matched_run else ""
        proxy_url = f"/api/workspace/preview_proxy/{run_id}/" if run_id and app_url else ""

        return jsonify({
            "ok": True,
            "path": abs_target.replace("\\", "/"),
            "signature": _compute_folder_signature(abs_target),
            "backend_running": bool(proxy_url),
            "run_id": run_id,
            "app_url": app_url,
            "proxy_url": proxy_url,
            "backend_entry_path": backend_entry.replace("\\", "/") if backend_entry else "",
        })

    @app.route("/api/workspace/preview_proxy/<run_id>/", defaults={"subpath": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    @app.route("/api/workspace/preview_proxy/<run_id>/<path:subpath>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def workspace_preview_proxy(run_id: str, subpath: str):
        return proxy_workspace_run_request(run_id, subpath)
