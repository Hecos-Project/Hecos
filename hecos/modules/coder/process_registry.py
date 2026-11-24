"""
hecos/modules/executor/process_registry.py
Thread-safe background app process lifecycle manager, log streaming, and singleton registry.
"""

from __future__ import annotations

import atexit
import os
import shlex
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .file_manager import AgentTracer, logger
from .http_probe import extract_local_urls, probe_local_http_url
from .process_watchdog import (
    discover_workspace_processes,
    record_started_pid,
    stop_processes_for_path,
    terminate_pid_tree,
    unrecord_pid,
)
from .test_runner import _build_script_invocation, _build_subproc_env, resolve_authorized_target


@dataclass
class ManagedRunEntry:
    run_id: str
    target_path: str
    name: str
    command_display: str
    cwd: str
    log_path: str
    started_at: float
    process: subprocess.Popen
    log_file_handle: Any = None
    ended_at: Optional[float] = None
    exit_code: Optional[int] = None
    stopped_by_user: bool = False
    detected_urls: List[str] = field(default_factory=list)


class ManagedProcessRegistry:
    """Thread-safe registry for running scripts and persistent workspace apps."""

    _MAX_HISTORY = 40

    def __init__(self):
        self._lock = threading.RLock()
        self._runs: Dict[str, ManagedRunEntry] = {}

    def _close_log_handle(self, entry: ManagedRunEntry) -> None:
        if entry.log_file_handle is not None:
            try:
                entry.log_file_handle.flush()
                entry.log_file_handle.close()
            except Exception:
                pass
            entry.log_file_handle = None

    def _refresh_entry(self, entry: ManagedRunEntry) -> str:
        code = entry.process.poll()
        if code is not None and entry.exit_code is None:
            entry.exit_code = code
            entry.ended_at = entry.ended_at or time.time()
            self._close_log_handle(entry)
            unrecord_pid(entry.run_id, pid=entry.process.pid)
        return "running" if entry.exit_code is None else ("stopped" if entry.stopped_by_user else "exited")

    def _read_log_text(self, log_path: str, offset: int = 0, max_bytes: int = 262144) -> tuple[str, int]:
        text, new_offset, _, _ = self._read_log_window(log_path, offset=offset, max_bytes=max_bytes)
        return text, new_offset

    def _read_log_window(
        self,
        log_path: str,
        offset: int = 0,
        max_bytes: int = 262144,
        tail_bytes: int = 0,
    ) -> tuple[str, int, int, bool]:
        if not os.path.isfile(log_path):
            return "", 0, 0, False
        try:
            file_size = os.path.getsize(log_path)
            safe_offset = max(0, min(int(offset), file_size))
            if tail_bytes and tail_bytes > 0 and safe_offset == 0 and file_size > tail_bytes:
                safe_offset = max(0, file_size - int(tail_bytes))
                read_limit = int(tail_bytes)
                truncated = True
            else:
                read_limit = int(max_bytes)
                truncated = (file_size - safe_offset) > read_limit

            with open(log_path, "rb") as fb:
                fb.seek(safe_offset)
                chunk = fb.read(read_limit)
                new_offset = fb.tell()
            if safe_offset > 0 and tail_bytes and chunk:
                nl_idx = chunk.find(b"\n")
                if 0 <= nl_idx < len(chunk) - 1:
                    chunk = chunk[nl_idx + 1:]
            return chunk.decode("utf-8", errors="replace"), new_offset, file_size, truncated
        except OSError:
            return "", offset, 0, False

    def _prune_old_runs_locked(self) -> None:
        finished = [e for e in self._runs.values() if self._refresh_entry(e) != "running"]
        if len(finished) <= self._MAX_HISTORY:
            return
        finished.sort(key=lambda e: e.started_at)
        for old in finished[: len(finished) - self._MAX_HISTORY]:
            self._runs.pop(old.run_id, None)
            try:
                if os.path.isfile(old.log_path):
                    os.remove(old.log_path)
            except OSError:
                pass

    @staticmethod
    def _extract_cli_port(extra_args: List[str]) -> Optional[int]:
        for idx, tok in enumerate(extra_args or []):
            t = str(tok).strip()
            if t.startswith("--port="):
                val = t.split("=", 1)[1]
                if val.isdigit():
                    return int(val)
            elif t in {"--port", "-p"} and idx + 1 < len(extra_args):
                val = str(extra_args[idx + 1]).strip()
                if val.isdigit():
                    return int(val)
        return None

    def _find_conflicting_running_ids_locked(self, abs_target: str, target_port: Optional[int]) -> List[str]:
        norm_target = os.path.normcase(os.path.abspath(abs_target))
        conflicts: List[str] = []
        port_token = f":{target_port}" if target_port else ""
        for rid, entry in self._runs.items():
            if self._refresh_entry(entry) != "running":
                continue
            if os.path.normcase(os.path.abspath(entry.target_path)) == norm_target:
                conflicts.append(rid)
                continue
            if port_token and any(port_token in u for u in (entry.detected_urls or [])):
                conflicts.append(rid)
        return conflicts

    def _stop_conflicting_runs(self, abs_target: str, extra_args: List[str]) -> None:
        target_port = self._extract_cli_port(extra_args)
        with self._lock:
            stale_ids = self._find_conflicting_running_ids_locked(abs_target, target_port)
        for old_rid in stale_ids:
            logger.info(
                f"[RUNNER] Stopping previous active run_id={old_rid} before restarting {os.path.basename(abs_target)}"
            )
            self.stop_run(old_rid)
        # Also release any orphaned OS processes from prior restarts holding this project
        target_dir = abs_target if os.path.isdir(abs_target) else os.path.dirname(abs_target)
        stop_processes_for_path(abs_target, registry=self, workspace_dir=target_dir)

    def _read_entry_snapshot(self, entry: ManagedRunEntry) -> tuple[str, str, int]:
        with self._lock:
            status = self._refresh_entry(entry)
            output_text, offset = self._read_log_text(entry.log_path, offset=0)
            entry.detected_urls = extract_local_urls(output_text)
            return status, output_text, offset

    def _build_finished_payload(
        self,
        entry: ManagedRunEntry,
        status: str,
        output_text: str,
        offset: int,
        require_stay_alive: bool,
    ) -> Dict[str, Any]:
        duration_ms = int(((entry.ended_at or time.time()) - entry.started_at) * 1000)
        ok = (entry.exit_code == 0)
        log_fn = logger.info if ok else logger.warning
        log_fn(
            f"[RUNNER] oneshot finished run_id={entry.run_id} name={entry.name} exit={entry.exit_code} duration_ms={duration_ms}"
        )
        AgentTracer.emit_action("run_script", entry.name, f"exit={entry.exit_code} ({duration_ms}ms)")
        payload: Dict[str, Any] = {
            "ok": False if (require_stay_alive and not ok) else ok,
            "status": status,
            "execution_type": "app" if (require_stay_alive and not ok) else "oneshot",
            "run_id": entry.run_id,
            "pid": entry.process.pid,
            "path": entry.target_path,
            "name": entry.name,
            "cwd": entry.cwd,
            "command": entry.command_display,
            "exit_code": entry.exit_code,
            "duration_ms": duration_ms,
            "offset": offset,
            "output": output_text or (f"(exited with code {entry.exit_code})" if require_stay_alive and not ok else "(completed with no output)"),
            "detected_urls": entry.detected_urls,
            "log_path": entry.log_path,
        }
        if require_stay_alive and not ok:
            payload["error"] = f"App exited immediately with code {entry.exit_code}."
        return payload

    def start_target(
        self,
        target_path: str,
        workspace_dir: str,
        sandbox_dir: str,
        *,
        args: str = "",
        wait_seconds: float = 1.5,
        strict_workspace_only: bool = True,
        require_stay_alive: bool = False,
        replace_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Launch an authorized script or app in workspace_dir, logging output under sandbox_dir/runs.
        """
        abs_target, err = resolve_authorized_target(
            target_path, workspace_dir, strict_workspace_only=strict_workspace_only
        )
        if err:
            return {"ok": False, "status": "error", "error": err, "output": err}
        if not os.path.isfile(abs_target):
            msg = f"Target is not a runnable file: {abs_target}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        try:
            extra_args = shlex.split(args.strip(), posix=(os.name != "nt")) if args and args.strip() else []
        except ValueError as exc:
            msg = f"Invalid arguments syntax: {exc}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        cmd, work_dir, display_cmd, build_err = _build_script_invocation(abs_target, extra_args, workspace_dir)
        if build_err or not cmd:
            return {"ok": False, "status": "error", "error": build_err or "Invalid command", "output": build_err or ""}

        if replace_existing:
            self._stop_conflicting_runs(abs_target, extra_args)

        runs_dir = os.path.join(os.path.abspath(sandbox_dir), "runs")
        os.makedirs(runs_dir, exist_ok=True)
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        log_path = os.path.join(runs_dir, f"{run_id}.log")
        logger.info(
            f"[RUNNER] start_target run_id={run_id} file={abs_target} cwd={work_dir} cmd={display_cmd} wait={wait_seconds}s"
        )

        ws_abs = os.path.abspath(workspace_dir)
        import_roots = [ws_abs, work_dir] if os.path.normcase(work_dir) != os.path.normcase(ws_abs) else [ws_abs]
        env = _build_subproc_env(import_roots)

        try:
            log_fh = open(log_path, "w", encoding="utf-8", errors="replace")
        except OSError as exc:
            msg = f"Unable to open run log '{log_path}': {exc}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=work_dir,
                env=env,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                creationflags=creationflags,
            )
        except Exception as exc:
            try:
                log_fh.close()
            except Exception:
                pass
            msg = f"Failed to start process: {exc}"
            return {"ok": False, "status": "error", "error": msg, "output": msg}

        entry = ManagedRunEntry(
            run_id=run_id,
            target_path=abs_target,
            name=os.path.basename(abs_target),
            command_display=display_cmd,
            cwd=work_dir,
            log_path=log_path,
            started_at=time.time(),
            process=proc,
            log_file_handle=log_fh,
        )

        with self._lock:
            self._prune_old_runs_locked()
            self._runs[run_id] = entry
        record_started_pid(
            run_id=run_id,
            pid=proc.pid,
            target_path=abs_target,
            cwd=work_dir,
            name=entry.name,
            command=display_cmd,
            started_at=entry.started_at,
        )
        logger.debug(f"[RUNNER] spawned PID={proc.pid} run_id={run_id} log={log_path}")

        wait_cap = max(0.2, min(float(wait_seconds or 1.5), 10.0))
        deadline = time.monotonic() + wait_cap
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.08)

        status, output_text, offset = self._read_entry_snapshot(entry)
        if status != "running":
            return self._build_finished_payload(entry, status, output_text, offset, require_stay_alive)

        if not entry.detected_urls and len(output_text) < 20:
            time.sleep(0.45)
            status, output_text, offset = self._read_entry_snapshot(entry)

        http_probe: Optional[Dict[str, Any]] = None
        if status == "running" and entry.detected_urls:
            http_probe = probe_local_http_url(entry.detected_urls[0], timeout=1.0, check_assets=True, retries=2)
            time.sleep(0.12)
            with self._lock:
                status = self._refresh_entry(entry)
                output_text, offset = self._read_log_text(entry.log_path, offset=0)

        logger.info(
            f"[RUNNER] app status={status} run_id={run_id} pid={proc.pid} urls={entry.detected_urls} probe={http_probe.get('summary') if http_probe else 'none'}"
        )
        AgentTracer.emit_action("start_app", entry.name, f"PID {proc.pid} ({run_id})")
        return {
            "ok": True if status == "running" else (entry.exit_code == 0),
            "status": status,
            "execution_type": "app" if status == "running" else "oneshot",
            "run_id": run_id,
            "pid": proc.pid,
            "path": abs_target,
            "name": entry.name,
            "cwd": work_dir,
            "command": display_cmd,
            "exit_code": entry.exit_code,
            "duration_ms": int((time.time() - entry.started_at) * 1000),
            "offset": offset,
            "output": output_text,
            "detected_urls": entry.detected_urls,
            "http_probe": http_probe,
            "log_path": log_path,
        }

    def get_run_log_path(self, run_id: str) -> Optional[tuple[str, str]]:
        with self._lock:
            entry = self._runs.get(run_id)
            if not entry or not entry.log_path or not os.path.isfile(entry.log_path):
                return None
            return entry.log_path, entry.name

    def resolve_run_id(self, run_id_hint: str) -> tuple[Optional[str], bool]:
        """Resolve exact run_id or placeholder hints ('latest', '<run_id...>') to the newest recorded run."""
        raw = (run_id_hint or "").strip()
        with self._lock:
            if raw in self._runs:
                return raw, False
            is_placeholder = (
                not raw
                or (raw.startswith("<") and raw.endswith(">"))
                or raw.lower() in {"latest", "last", "current", "auto", "previous", "prev"}
            )
            if is_placeholder and self._runs:
                newest = max(
                    self._runs.values(),
                    key=lambda e: (1 if self._refresh_entry(e) == "running" else 0, e.started_at),
                )
                return newest.run_id, True
        return None, False

    def get_logs(self, run_id: str, offset: int = 0, tail_lines: int = 0, tail_bytes: int = 0) -> Dict[str, Any]:
        resolved_id, was_resolved = self.resolve_run_id(run_id)
        with self._lock:
            entry = self._runs.get(resolved_id) if resolved_id else None
            if not entry:
                recent = sorted(self._runs.values(), key=lambda e: e.started_at, reverse=True)[:5]
                recent_hint = (
                    " Recent run_ids: " + ", ".join(f"{e.run_id} ({e.name}, {self._refresh_entry(e)})" for e in recent)
                    if recent
                    else " No active/recent managed runs found."
                )
                return {"ok": False, "error": f"Unknown run_id: {run_id}.{recent_hint}"}
            status = self._refresh_entry(entry)
            text, new_offset, total_bytes, truncated = self._read_log_window(
                entry.log_path,
                offset=offset,
                max_bytes=262144,
                tail_bytes=tail_bytes,
            )
            if text or total_bytes > 0:
                if offset == 0 and not truncated:
                    url_scan_text = text
                else:
                    head_txt, _ = self._read_log_text(entry.log_path, offset=0, max_bytes=131072)
                    url_scan_text = head_txt if head_txt == text else f"{head_txt}\n{text}"
                entry.detected_urls = extract_local_urls(url_scan_text)
            if tail_lines and tail_lines > 0 and text:
                lines = text.splitlines()
                text = "\n".join(lines[-tail_lines:])
            return {
                "ok": True,
                "run_id": entry.run_id,
                "resolved_from": run_id if was_resolved else None,
                "name": entry.name,
                "path": entry.target_path,
                "pid": entry.process.pid,
                "status": status,
                "exit_code": entry.exit_code,
                "offset": new_offset,
                "total_bytes": total_bytes,
                "truncated": truncated,
                "chunk": text,
                "detected_urls": list(entry.detected_urls),
                "duration_ms": int(((entry.ended_at or time.time()) - entry.started_at) * 1000),
            }

    def stop_run(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._runs.get(run_id)
            if not entry:
                return {"ok": False, "error": f"Unknown run_id: {run_id}"}
            status = self._refresh_entry(entry)
            if status != "running":
                return {
                    "ok": True,
                    "run_id": run_id,
                    "status": status,
                    "exit_code": entry.exit_code,
                    "message": "Process already finished.",
                }
            entry.stopped_by_user = True
            proc = entry.process

        try:
            terminate_pid_tree(proc.pid, timeout=2.0)
            try:
                proc.wait(timeout=1.5)
            except Exception:
                pass
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        unrecord_pid(run_id, pid=proc.pid)
        with self._lock:
            status = self._refresh_entry(entry)
            logger.info(f"[RUNNER] stop_run run_id={run_id} pid={proc.pid} status={status} exit={entry.exit_code}")
            AgentTracer.emit_action("stop_app", entry.name, f"{run_id} ({status})")
            return {
                "ok": True,
                "run_id": run_id,
                "status": status,
                "exit_code": entry.exit_code,
                "message": f"Stopped {entry.name} (PID {proc.pid}).",
            }

    def stop_by_path(self, target_path: str, workspace_dir: Optional[str] = None) -> Dict[str, Any]:
        """Stop all managed runs and orphaned OS processes locking `target_path`."""
        res = stop_processes_for_path(target_path, registry=self, workspace_dir=workspace_dir)
        AgentTracer.emit_action("stop_app", os.path.basename(target_path), f"stopped={res.get('stopped_count', 0)}")
        return res

    def stop_pid(self, pid: int, workspace_dir: Optional[str] = None) -> Dict[str, Any]:
        """Stop a tracked or orphaned workspace process by OS PID."""
        pid_int = int(pid)
        with self._lock:
            for entry in self._runs.values():
                if self._refresh_entry(entry) == "running" and int(entry.process.pid) == pid_int:
                    return self.stop_run(entry.run_id)

        if workspace_dir:
            live = discover_workspace_processes(workspace_dir=workspace_dir)
            if not any(int(p["pid"]) == pid_int for p in live):
                return {"ok": False, "error": f"PID {pid_int} is not an active workspace process."}

        ok = terminate_pid_tree(pid_int, timeout=2.0)
        unrecord_pid(pid=pid_int)
        if ok:
            AgentTracer.emit_action("stop_app", f"PID {pid_int}", "stopped")
            return {"ok": True, "pid": pid_int, "status": "stopped", "message": f"Stopped process PID {pid_int}."}
        return {"ok": False, "pid": pid_int, "error": f"Could not terminate PID {pid_int}."}

    def stop_all_runs(self, *, include_orphans: bool = False, workspace_dir: Optional[str] = None) -> Dict[str, Any]:
        """Stop all active managed workspace processes (and optionally orphan OS workspace apps)."""
        with self._lock:
            active_ids = [rid for rid, e in self._runs.items() if self._refresh_entry(e) == "running"]
        stopped_rids: List[str] = []
        stopped_pids: List[int] = []
        for rid in active_ids:
            res = self.stop_run(rid)
            if res.get("ok"):
                stopped_rids.append(rid)

        if include_orphans and workspace_dir:
            res_ws = stop_processes_for_path(workspace_dir, registry=self, workspace_dir=workspace_dir)
            stopped_pids.extend(res_ws.get("stopped_pids") or [])

        return {
            "ok": True,
            "stopped_run_ids": stopped_rids,
            "stopped_pids": stopped_pids,
            "stopped_count": len(stopped_rids) + len(stopped_pids),
        }

    def list_all_processes(self, workspace_dir: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tracked runs merged with any orphaned live OS workspace processes."""
        items = self.list_runs()
        for it in items:
            it["source"] = "managed"

        if not workspace_dir:
            return items

        managed_running_pids = {int(it["pid"]) for it in items if it.get("status") == "running" and it.get("pid")}
        now = time.time()
        for op in discover_workspace_processes(workspace_dir=workspace_dir):
            pid = int(op["pid"])
            if pid in managed_running_pids:
                continue
            items.insert(0, {
                "run_id": f"os_{pid}",
                "name": f"{op.get('project_name') or 'workspace'}/{op.get('name') or 'process'}",
                "project_name": op.get("project_name") or "",
                "path": op.get("path") or "",
                "command": op.get("command") or "",
                "cwd": op.get("cwd") or "",
                "pid": pid,
                "status": "running",
                "source": "orphan_os",
                "exit_code": None,
                "started_at": op.get("started_at") or now,
                "duration_ms": int(max(0.0, now - float(op.get("started_at") or now)) * 1000),
                "detected_urls": [],
            })
        return items

    def list_runs(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = []
            for entry in sorted(self._runs.values(), key=lambda e: e.started_at, reverse=True):
                status = self._refresh_entry(entry)
                if not entry.detected_urls:
                    full_text = self._read_log_text(entry.log_path, offset=0)[0]
                    entry.detected_urls = extract_local_urls(full_text)
                items.append({
                    "run_id": entry.run_id,
                    "name": entry.name,
                    "path": entry.target_path,
                    "command": entry.command_display,
                    "cwd": entry.cwd,
                    "pid": entry.process.pid,
                    "status": status,
                    "exit_code": entry.exit_code,
                    "started_at": entry.started_at,
                    "duration_ms": int(((entry.ended_at or time.time()) - entry.started_at) * 1000),
                    "detected_urls": list(entry.detected_urls),
                })
            return items


_REGISTRY = ManagedProcessRegistry()


def _cleanup_registry_on_exit() -> None:
    try:
        _REGISTRY.stop_all_runs(include_orphans=False)
    except Exception:
        pass


atexit.register(_cleanup_registry_on_exit)


def get_process_registry() -> ManagedProcessRegistry:
    """Return the global ManagedProcessRegistry singleton."""
    return _REGISTRY
