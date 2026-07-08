"""
hecos/core/ipc/protocol.py
─────────────────────────────────────────────────────────────────────────────
IPC Protocol — JSON Lines format for Core <-> Plugin subprocess communication.
Only stdlib is used. Safe to import in an isolated plugin subprocess.
─────────────────────────────────────────────────────────────────────────────

MESSAGE TYPES (Core → Plugin):
  {"type": "call",     "id": "<uuid>", "method": "<str>", "kwargs": {...}}
  {"type": "info",     "id": "<uuid>"}
  {"type": "shutdown"}

MESSAGE TYPES (Plugin → Core):
  {"type": "result",   "id": "<uuid>", "value": ..., "ok": true}
  {"type": "result",   "id": "<uuid>", "error": "<str>", "ok": false}
  {"type": "manifest", "id": "<uuid>", "data": {...}}
  {"type": "log",      "level": "info|debug|warning|error", "msg": "<str>"}
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional


# ── Outbound helpers (Core → Plugin) ─────────────────────────────────────────

def make_call(method: str, kwargs: Optional[Dict[str, Any]] = None) -> str:
    """Build a 'call' JSON-Line message."""
    return json.dumps({
        "type": "call",
        "id": str(uuid.uuid4()),
        "method": method,
        "kwargs": kwargs or {},
    }) + "\n"


def make_info() -> str:
    """Build an 'info' JSON-Line message (request manifest from plugin)."""
    return json.dumps({
        "type": "info",
        "id": str(uuid.uuid4()),
    }) + "\n"


def make_shutdown() -> str:
    """Build a 'shutdown' JSON-Line message."""
    return json.dumps({"type": "shutdown"}) + "\n"


# ── Response parser (Core, reading from Plugin stdout) ────────────────────────

def parse_response(line: str) -> Dict[str, Any]:
    """Parse a JSON-Line response from the plugin subprocess.
    Returns the decoded dict, or a synthetic error dict on failure."""
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError as e:
        return {"type": "result", "id": None, "ok": False, "error": f"Protocol parse error: {e}  raw={line!r}"}
