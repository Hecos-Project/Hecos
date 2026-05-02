import os
import sys
import json
import threading
import subprocess
from flask import request, jsonify

# File-based queue for cross-process communication (avoids multi-worker isolation)
_QUEUE_LOCK = threading.Lock()

def _get_queue_path():
    """Returns the path to the bridge command queue file."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(root, ".bridge_queue.json")

def _read_queue():
    path = _get_queue_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _write_queue(cmds: list):
    path = _get_queue_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cmds, f)
    except Exception:
        pass

def init_bridge_routes(app, logger):
    """
    Initializes the bridge endpoints for Session 0 -> Session 1 communication.
    Uses a file-based queue to persist commands across Flask worker processes.
    """

    @app.route("/api/bridge/command", methods=["POST"])
    def bridge_command():
        """WebUI (or Core) calls this to request a GUI action from the Tray App."""
        try:
            data = request.get_json(force=True) or {}
            cmd  = data.get("cmd")
            path = data.get("path")
            
            if not cmd:
                return jsonify({"ok": False, "error": "Missing command"}), 400
                
            if cmd == "open_folder" and path:
                clean_path = os.path.normpath(path)
                if os.path.exists(clean_path):
                    if sys.platform == "win32":
                        os.startfile(clean_path)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", clean_path])
                    else:
                        subprocess.Popen(["xdg-open", clean_path])
                    logger.info(f"[BRIDGE] Opened folder natively: {clean_path}")
                    return jsonify({"ok": True, "msg": "Folder opened"})
                else:
                    return jsonify({"ok": False, "error": "Path not found"}), 404
                    
            return jsonify({"ok": False, "error": "Unknown command"}), 400
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/bridge/poll", methods=["GET"])
    def bridge_poll():
        """Tray App (Session 1) calls this to check for pending actions."""
        try:
            with _QUEUE_LOCK:
                cmds = _read_queue()
                if not cmds:
                    return jsonify({"ok": True, "commands": []})
                
                # Clear the queue and return commands
                _write_queue([])
                
            logger.info(f"[BRIDGE] Commands dispatched to Tray: {[c['cmd'] for c in cmds]}")
            return jsonify({"ok": True, "commands": cmds})
        except Exception as e:
            logger.error(f"[BRIDGE] Poll error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
