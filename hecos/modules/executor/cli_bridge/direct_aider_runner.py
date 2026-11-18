"""
hecos/modules/executor/cli_bridge/direct_aider_runner.py
Background streaming runner for invoking Aider CLI directly from Monaco IDE or
Workspace Runner without waiting for an outer Hecos Chat LLM loop turn.
Streams live stdout lines, records milestones into `action_feed`, and performs
automatic post-run syntax & web diagnostics checks.
"""

from __future__ import annotations

import os
import secrets
import shutil
import tempfile
import threading
import time
from typing import Any, Dict, List

from ..aider_bridge import (
    _VERIFY_EXTS,
    _collect_touched_files,
    _snapshot_git_dirty_state,
    _spawn_aider_process,
    _write_temp_model_settings,
    resolve_aider_command,
    resolve_aider_runtime_settings,
)
from ..dev_tools import check_syntax_tool, inspect_web_project_issues
from ..file_manager import _is_safe_path
from ..git_tools import _resolve_repo_root
from ..process_watchdog import terminate_pid_tree
from .action_feed import record_action_event
from .terminal_launcher import resolve_project_cwd

_TASKS_LOCK = threading.Lock()
_DIRECT_TASKS: Dict[str, Dict[str, Any]] = {}
_MAX_DIRECT_TASKS = 40


def start_direct_aider_task(
    target_path: str,
    instruction: str,
    files: str = "",
    model: str = "",
    workspace_dir: str = "",
    timeout_seconds: int = 240,
) -> Dict[str, Any]:
    """
    Start a direct non-blocking Aider coding task on `target_path` and stream its output.
    """
    clean_inst = str(instruction or "").strip()
    if not clean_inst:
        return {"ok": False, "error": "Aider instruction cannot be empty."}

    cwd = resolve_project_cwd(target_path, workspace_dir=workspace_dir)
    if not _is_safe_path(cwd):
        return {"ok": False, "error": "Protected path."}

    runtime = resolve_aider_runtime_settings(explicit_model=model)
    if not runtime.get("enabled", True):
        return {"ok": False, "error": "Aider sidecar is disabled in EXECUTOR settings."}

    base_cmd = resolve_aider_command()
    if not base_cmd:
        return {"ok": False, "error": "Isolated Aider CLI is not installed in tools/aider_env."}

    ws_abs = os.path.abspath(workspace_dir or cwd)
    allow_git_init = os.path.normcase(cwd) != os.path.normcase(ws_abs)
    repo_root, repo_err = _resolve_repo_root(cwd, auto_init=allow_git_init)
    if repo_err or not repo_root:
        repo_root = cwd

    explicit_files: List[str] = []
    raw_files = str(files or "").strip()
    if not raw_files and target_path and os.path.isfile(os.path.abspath(target_path)):
        explicit_files.append(os.path.abspath(target_path))
    elif raw_files:
        for rf in raw_files.split(","):
            fc = rf.strip()
            if not fc:
                continue
            cand = os.path.abspath(fc if os.path.isabs(fc) else os.path.join(repo_root, fc))
            if os.path.isfile(cand) and _is_safe_path(cand):
                explicit_files.append(cand)

    task_id = f"aider_{int(time.time())}_{secrets.token_hex(3)}"
    chosen_model = runtime["model"]
    num_ctx = int(runtime["num_ctx"])

    task_entry: Dict[str, Any] = {
        "task_id": task_id,
        "status": "running",
        "repo_root": repo_root,
        "model": chosen_model,
        "num_ctx": num_ctx,
        "instruction": clean_inst,
        "files": [os.path.relpath(f, repo_root).replace("\\", "/") for f in explicit_files],
        "lines": [
            f"[Direct Aider] Launching {chosen_model} (ctx={num_ctx}) in {repo_root}",
            f"[Instruction] {clean_inst}",
        ],
        "touched_files": [],
        "diagnostics": [],
        "exit_code": None,
        "pid": None,
        "started_at": time.time(),
        "finished_at": None,
    }

    with _TASKS_LOCK:
        if len(_DIRECT_TASKS) >= _MAX_DIRECT_TASKS:
            oldest = sorted(_DIRECT_TASKS.keys(), key=lambda k: _DIRECT_TASKS[k]["started_at"])[:10]
            for k in oldest:
                if _DIRECT_TASKS[k]["status"] != "running":
                    _DIRECT_TASKS.pop(k, None)
        _DIRECT_TASKS[task_id] = task_entry

    record_action_event(
        "aider_direct",
        f"[{chosen_model}] {os.path.basename(repo_root)}: {clean_inst[:120]}",
        "Starting direct Aider task...",
        status="running",
    )

    worker = threading.Thread(
        target=_run_direct_aider_worker,
        args=(task_id, base_cmd, runtime, repo_root, explicit_files, clean_inst, timeout_seconds),
        daemon=True,
    )
    worker.start()

    return {
        "ok": True,
        "task_id": task_id,
        "status": "running",
        "model": chosen_model,
        "num_ctx": num_ctx,
        "repo_root": repo_root.replace("\\", "/"),
    }


def _run_direct_aider_worker(
    task_id: str,
    base_cmd: List[str],
    runtime: Dict[str, Any],
    repo_root: str,
    explicit_files: List[str],
    instruction: str,
    timeout_seconds: int,
) -> None:
    chosen_model = runtime["model"]
    before_state = _snapshot_git_dirty_state(repo_root)
    tmp_settings = _write_temp_model_settings(chosen_model, runtime["num_ctx"], runtime["edit_format"])
    tmp_hist_dir = tempfile.mkdtemp(prefix="hecos_direct_aider_")
    input_hist = os.path.join(tmp_hist_dir, "input.history")
    chat_hist = os.path.join(tmp_hist_dir, "chat.history.md")

    cmd: List[str] = [
        *base_cmd,
        "--yes-always",
        "--no-auto-commits",
        "--no-pretty",
        "--no-stream",
        "--no-analytics",
        "--no-check-update",
        "--no-restore-chat-history",
        "--no-gitignore",
        "--no-suggest-shell-commands",
        "--disable-playwright",
        "--encoding", "utf-8",
        "--input-history-file", input_hist,
        "--chat-history-file", chat_hist,
        "--model-settings-file", tmp_settings,
        "--auto-lint" if runtime["auto_lint"] else "--no-auto-lint",
        "--model", chosen_model,
        "--message", instruction,
        *explicit_files,
    ]

    env = os.environ.copy()
    if runtime.get("ollama_base"):
        env.setdefault("OLLAMA_API_BASE", str(runtime["ollama_base"]))
    for k, v in (runtime.get("env_keys") or {}).items():
        if v:
            env.setdefault(k, str(v))
    env.setdefault("AIDER_NO_BROWSER", "1")
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    t_limit = max(20, min(int(timeout_seconds or 240), 600))
    timed_out = threading.Event()
    proc = None

    try:
        proc = _spawn_aider_process(cmd, cwd=repo_root, env=env)
        with _TASKS_LOCK:
            if task_id in _DIRECT_TASKS:
                _DIRECT_TASKS[task_id]["pid"] = proc.pid

        def _on_timeout():
            timed_out.set()
            if proc and proc.pid:
                terminate_pid_tree(proc.pid)

        timer = threading.Timer(t_limit, _on_timeout)
        timer.daemon = True
        timer.start()
        try:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                line = raw_line.rstrip("\r\n")
                with _TASKS_LOCK:
                    if task_id in _DIRECT_TASKS:
                        _DIRECT_TASKS[task_id]["lines"].append(line)
                stripped = line.strip()
                if stripped and stripped.startswith((
                    "Applied edit", "Wrote ", "Error", "Warning", "Tokens:", "Added ", "Commit ",
                )):
                    record_action_event("aider_direct", f"[{chosen_model}]", stripped[:240], status="info")
            proc.wait(timeout=5)
        finally:
            timer.cancel()
            if proc and proc.stdout:
                try:
                    proc.stdout.close()
                except Exception:
                    pass

        with _TASKS_LOCK:
            task = _DIRECT_TASKS.get(task_id)
            if not task:
                return
            if task["status"] == "stopped":
                task["finished_at"] = time.time()
                return

        if timed_out.is_set():
            with _TASKS_LOCK:
                task = _DIRECT_TASKS[task_id]
                task["status"] = "failed"
                task["lines"].append(f"[Direct Aider] Timed out after {t_limit}s.")
                task["finished_at"] = time.time()
            record_action_event("aider_direct", f"Timeout ({t_limit}s)", repo_root, status="error")
            return

        rc = proc.returncode if proc else 1
        touched = _collect_touched_files(repo_root, before_state, explicit_files)
        rel_touched = [os.path.relpath(p, repo_root).replace("\\", "/") for p in touched]
        diags: List[str] = []
        for fpath in touched[:20]:
            ext = os.path.splitext(fpath)[1].lower()
            if ext in _VERIFY_EXTS:
                syn = check_syntax_tool(fpath)
                if "SYNTAX ERROR" in syn:
                    diags.append(syn)
                if ext in (".py", ".html", ".htm"):
                    diags.extend(inspect_web_project_issues(fpath))

        with _TASKS_LOCK:
            task = _DIRECT_TASKS[task_id]
            task["exit_code"] = rc
            task["touched_files"] = rel_touched
            task["diagnostics"] = diags
            task["status"] = "completed" if rc == 0 else "failed"
            task["finished_at"] = time.time()
            if rel_touched:
                task["lines"].append(f"[Direct Aider] Touched files: {', '.join(rel_touched)}")
            for d in diags:
                task["lines"].append(f"[Diagnostic] {d}")
            task["lines"].append(f"[Direct Aider] Finished (exit={rc}).")

        record_action_event(
            "aider_direct",
            f"Completed in {os.path.basename(repo_root)} (exit={rc})",
            f"Touched: {', '.join(rel_touched) or 'none'}",
            status="ok" if rc == 0 else "error",
        )
    except Exception as exc:
        with _TASKS_LOCK:
            if task_id in _DIRECT_TASKS:
                _DIRECT_TASKS[task_id]["status"] = "failed"
                _DIRECT_TASKS[task_id]["lines"].append(f"[Error] {exc}")
                _DIRECT_TASKS[task_id]["finished_at"] = time.time()
        record_action_event("aider_direct", "Execution error", str(exc), status="error")
    finally:
        for p in (tmp_settings,):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass
        if os.path.exists(tmp_hist_dir):
            shutil.rmtree(tmp_hist_dir, ignore_errors=True)


def get_direct_aider_task(task_id: str, offset: int = 0) -> Dict[str, Any]:
    """Return incremental output lines and status for a direct Aider task."""
    with _TASKS_LOCK:
        task = _DIRECT_TASKS.get(str(task_id or "").strip())
        if not task:
            return {"ok": False, "error": "Direct Aider task not found."}
        lines = task["lines"]
        start = max(0, min(int(offset or 0), len(lines)))
        chunk = "\n".join(lines[start:])
        if chunk:
            chunk += "\n"
        return {
            "ok": True,
            "task_id": task["task_id"],
            "status": task["status"],
            "model": task["model"],
            "num_ctx": task["num_ctx"],
            "repo_root": task["repo_root"].replace("\\", "/"),
            "chunk": chunk,
            "offset": len(lines),
            "touched_files": list(task["touched_files"]),
            "diagnostics": list(task["diagnostics"]),
            "exit_code": task["exit_code"],
        }


def stop_direct_aider_task(task_id: str) -> Dict[str, Any]:
    """Terminate an active direct Aider task."""
    with _TASKS_LOCK:
        task = _DIRECT_TASKS.get(str(task_id or "").strip())
        if not task:
            return {"ok": False, "error": "Task not found."}
        pid = task.get("pid")
        task["status"] = "stopped"
        task["lines"].append("[Direct Aider] Stopped by user.")
        task["finished_at"] = time.time()

    if pid:
        terminate_pid_tree(int(pid))
    record_action_event("aider_direct", f"Stopped task {task_id}", f"pid={pid}", status="info")
    return {"ok": True, "task_id": task_id, "status": "stopped"}
