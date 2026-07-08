"""
hecos/core/ipc/runner.py
─────────────────────────────────────────────────────────────────────────────
Plugin Runner — Entry point for each isolated HPM plugin subprocess.

This file is copied into the plugin's own directory by the Hecos Builder.
It runs inside the plugin's venv. It must NOT import anything from hecos.core.
─────────────────────────────────────────────────────────────────────────────

Usage (launched by ModuleBus):
    C:\\hecos\\hpm\\image_gen\\venv\\Scripts\\python.exe runner.py

Protocol: JSON Lines via stdin/stdout.
"""
from __future__ import annotations

import sys
import os
import json
import traceback


# ─── Minimal IPC helpers (no hecos.core dependency) ──────────────────────────

def _send(obj: dict):
    """Serialize and flush a message to stdout."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _log(level: str, msg: str):
    """Forward a log line to the Hecos core via IPC."""
    _send({"type": "log", "level": level, "msg": msg})


# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    # The runner is invoked from inside the plugin directory.
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Dynamically import the plugin's main module
    try:
        import importlib
        plugin_module = importlib.import_module("main")
        tools_instance = getattr(plugin_module, "tools", None)
        if tools_instance is None:
            _send({"type": "log", "level": "error", "msg": "Plugin has no 'tools' attribute."})
            sys.exit(1)
    except Exception as e:
        _send({"type": "log", "level": "error", "msg": f"Failed to import plugin main: {traceback.format_exc()}"})
        sys.exit(1)

    _log("info", f"Plugin runner ready. Tag: {getattr(tools_instance, 'tag', 'UNKNOWN')}")

    # ── Message loop ─────────────────────────────────────────────────────────
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError:
            _send({"type": "result", "id": None, "ok": False, "error": f"Invalid JSON: {raw_line!r}"})
            continue

        msg_type = msg.get("type")
        msg_id   = msg.get("id")

        # ── Info request: return manifest ──────────────────────────────────
        if msg_type == "info":
            manifest_data = {}
            for attr in ("tag", "desc", "description", "icon", "category", "routing_instructions", "slash_commands"):
                val = getattr(tools_instance, attr, None)
                if val is not None:
                    manifest_data[attr] = val
            _send({"type": "manifest", "id": msg_id, "data": manifest_data})
            continue

        # ── Shutdown ───────────────────────────────────────────────────────
        if msg_type == "shutdown":
            _log("info", "Plugin subprocess shutting down.")
            break

        # ── Method call ────────────────────────────────────────────────────
        if msg_type == "call":
            method_name = msg.get("method", "")
            kwargs      = msg.get("kwargs", {})

            if not hasattr(tools_instance, method_name):
                _send({"type": "result", "id": msg_id, "ok": False,
                       "error": f"Method '{method_name}' not found on tools."})
                continue

            try:
                method = getattr(tools_instance, method_name)
                result = method(**kwargs) if isinstance(kwargs, dict) else method(kwargs)
                _send({"type": "result", "id": msg_id, "ok": True, "value": result})
            except Exception as e:
                _send({"type": "result", "id": msg_id, "ok": False,
                       "error": traceback.format_exc()})
            continue

        # ── Unknown message type ───────────────────────────────────────────
        _send({"type": "result", "id": msg_id, "ok": False, "error": f"Unknown message type: {msg_type!r}"})


if __name__ == "__main__":
    main()
