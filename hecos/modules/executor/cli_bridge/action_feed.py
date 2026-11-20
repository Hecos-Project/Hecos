"""
hecos/modules/executor/cli_bridge/action_feed.py
Thread-safe live ring buffer and log file writer for Hecos coding & agent actions.
Powers both the in-browser Monaco IDE / Workspace Runner 'Live Actions' tab
and the native Windows PowerShell 'Hecos - Coding Action Trace' console.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List

from hecos.core.constants import LOGS_DIR

_FEED_LOCK = threading.Lock()
_MAX_BUFFER_SIZE = 400
_MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB cap before rotation
_ACTION_BUFFER: List[Dict[str, Any]] = []
_SEQ_COUNTER = 0


def get_actions_log_path() -> str:
    """Return absolute path to `logs/hecos_actions.log`, creating directory if needed."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    return os.path.join(LOGS_DIR, "hecos_actions.log")


def _infer_status(tool_name: str, command: str, output: str, explicit_status: str = "") -> str:
    if explicit_status:
        return explicit_status
    combined = f"{tool_name} {command} {output}".lower()
    if any(k in combined for k in ("[error]", "syntax error", "failed", "timed out", "access denied", "traceback")):
        return "error"
    if any(k in combined for k in ("starting", "running", "launching")):
        return "running"
    return "ok"


def _append_to_actions_log(entry: Dict[str, Any]) -> None:
    log_path = get_actions_log_path()
    try:
        if os.path.isfile(log_path) and os.path.getsize(log_path) > _MAX_LOG_BYTES:
            bak = log_path + ".1"
            try:
                if os.path.exists(bak):
                    os.remove(bak)
                os.replace(log_path, bak)
            except OSError:
                pass

        ts_str = entry["iso_time"]
        tag = str(entry["tool_name"] or "ACTION").upper()
        status = str(entry["status"] or "ok").upper()
        cmd = str(entry["command"] or "").replace("\r", " ").replace("\n", " ").strip()
        out = str(entry["output"] or "").strip()

        lines = [f"{ts_str} [ACTION:{tag}] [{status}] $ {cmd}"]
        if out:
            for raw_ln in out.splitlines()[:12]:
                clean_ln = raw_ln.rstrip()
                if clean_ln:
                    lines.append(f"  | {clean_ln[:260]}")
        with open(log_path, "a", encoding="utf-8", errors="replace") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        pass


def record_action_event(
    tool_name: str,
    command: str,
    output: str = "",
    status: str = "",
) -> Dict[str, Any]:
    """Record a coding/tool action into the live ring buffer and `hecos_actions.log`."""
    global _SEQ_COUNTER
    now = time.time()
    iso_time = datetime.fromtimestamp(now).strftime("%H:%M:%S")
    clean_tool = str(tool_name or "ACTION").strip()
    clean_cmd = str(command or "").strip()
    clean_out = str(output or "").strip()
    if len(clean_out) > 1200:
        clean_out = clean_out[:1200] + "\n...[truncated]"

    resolved_status = _infer_status(clean_tool, clean_cmd, clean_out, explicit_status=status)

    with _FEED_LOCK:
        _SEQ_COUNTER += 1
        entry: Dict[str, Any] = {
            "seq": _SEQ_COUNTER,
            "ts": now,
            "iso_time": iso_time,
            "tool_name": clean_tool,
            "command": clean_cmd,
            "output": clean_out,
            "status": resolved_status,
        }
        _ACTION_BUFFER.append(entry)
        if len(_ACTION_BUFFER) > _MAX_BUFFER_SIZE:
            del _ACTION_BUFFER[: len(_ACTION_BUFFER) - _MAX_BUFFER_SIZE]

    _append_to_actions_log(entry)
    return entry


def get_action_events(since_seq: int = 0, limit: int = 120) -> Dict[str, Any]:
    """Fetch action events with `seq > since_seq` for incremental UI polling."""
    s_seq = max(0, int(since_seq or 0))
    cap = max(1, min(int(limit or 120), _MAX_BUFFER_SIZE))
    with _FEED_LOCK:
        if s_seq <= 0:
            items = list(_ACTION_BUFFER[-cap:])
        else:
            items = [e for e in _ACTION_BUFFER if int(e["seq"]) > s_seq][-cap:]
        latest_seq = _SEQ_COUNTER

    return {
        "ok": True,
        "events": items,
        "latest_seq": latest_seq,
        "log_path": get_actions_log_path().replace("\\", "/"),
    }


def clear_action_events() -> Dict[str, Any]:
    """Clear in-memory action events buffer."""
    with _FEED_LOCK:
        _ACTION_BUFFER.clear()
        latest = _SEQ_COUNTER
    return {"ok": True, "latest_seq": latest}
