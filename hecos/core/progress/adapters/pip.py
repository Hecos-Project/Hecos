"""
hecos/core/progress/adapters/pip.py
─────────────────────────────────────────────────────────────────────────────
Pip execution adapter with real-time percentage and phase parsing.
Runs pip with '--progress-bar=raw' to parse byte/item counts directly,
and surfaces milestones (Collecting, Downloading, Installing) to the task.
Supports process cancellation.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import re
import sys
import subprocess
from typing import List, Optional, Tuple, Dict, Callable, Any
from hecos.core.progress.model import Task, CancellationRequested

_PROGRESS_RAW_RE = re.compile(r"^Progress\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE)

# Standard phase layout used by callers that want milestone-based progress:
#   ("resolve", weight, label), ("download", ...), ("install", ...)
PIP_PHASES = [("resolve", 15, "Resolving"), ("download", 50, "Download"), ("install", 35, "Installing")]


def _has_phase(task: Task, key: str) -> bool:
    return any(p.key == key for p in task.phases)


def run_pip(
    pip_args: List[str],
    task: Optional[Task] = None,
    cwd: Optional[str] = None,
    python_exe: Optional[str] = None,
    extra_env: Optional[Dict[str, str]] = None,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[int, str]:
    """
    Executes a pip command, parsing progress output and updating task metrics.
    Returns (returncode, combined_stdout_stderr).
    """
    py = python_exe or sys.executable
    cmd = [py, "-m", "pip"] + list(pip_args)

    # Ensure pip outputs machine-readable progress if not already specified
    if "--progress-bar" not in " ".join(cmd):
        cmd.extend(["--progress-bar", "raw"])

    import os
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if extra_env:
        env.update(extra_env)

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines = []

    # Wire cancellation handler
    if task:
        def _kill():
            try:
                proc.terminate()
                proc.kill()
            except Exception:
                pass
        task.on_cancel = _kill

    try:
        for line in iter(proc.stdout.readline, ""):
            output_lines.append(line)
            clean = line.strip()
            if not clean:
                continue

            if task:
                task.check_cancelled()

            # Check raw progress: "Progress 12345 of 67890"
            m = _PROGRESS_RAW_RE.match(clean)
            if m:
                cur = int(m.group(1))
                tot = int(m.group(2))
                if task:
                    task.advance(bytes_done=cur, total_bytes=tot)
                if on_progress:
                    on_progress({
                        "step": "pip_progress",
                        "bytes_done": cur,
                        "bytes_total": tot,
                        "percent": round(cur / tot * 100, 1) if tot > 0 else 0,
                    })
                continue

            # Check semantic stages
            if on_progress:
                on_progress({"step": "pip_log", "message": clean})

            if task:
                if clean.startswith("Collecting ") or clean.startswith("Requirement already satisfied"):
                    if _has_phase(task, "resolve"):
                        task.phase("resolve", message=clean[:70])
                    task.advance(message=clean, log=clean)
                elif clean.startswith("Downloading ") or clean.startswith("Using cached "):
                    if _has_phase(task, "download"):
                        task.phase("download", message=clean[:70])
                    task.advance(message=clean[:55], log=clean)
                    if clean.startswith("Using cached "):
                        task.advance(percent=100.0)
                elif "Installing collected packages" in clean or clean.startswith("Attempting uninstall"):
                    if _has_phase(task, "install"):
                        task.phase("install", message="Installing pip packages...")
                        task.advance(percent=40.0)
                    task.advance(message="Installing pip packages...", log=clean)
                elif clean.startswith("Successfully installed"):
                    if _has_phase(task, "install"):
                        task.advance(percent=100.0)
                    task.advance(message="Pip dependencies installed.", log=clean)
                elif clean.startswith("ERROR:") or clean.startswith("error:"):
                    task.advance(log=clean)
                else:
                    task.advance(log=clean[:120])

        proc.stdout.close()
        retcode = proc.wait()

        if task and task.is_cancelled:
            raise CancellationRequested("Pip install interrupted by cancellation.")

        return retcode, "".join(output_lines)

    except CancellationRequested:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    except Exception as exc:
        try:
            proc.kill()
        except Exception:
            pass
        raise exc
