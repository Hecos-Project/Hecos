import os
import json
from datetime import datetime
from flask import request, jsonify, Response, stream_with_context
from zentra.core.constants import LOGS_DIR
from zentra.core.logging.hub import get_hub
import queue

def init_log_routes(app, cfg_mgr, root_dir, logger, get_sm=None):
    @app.route("/api/logs/files", methods=["GET"])
    def list_log_files():
        """Returns a list of all log files in the logs directory."""
        try:
            files = []
            for f in os.listdir(LOGS_DIR):
                if f.endswith(".log") or f.endswith(".txt"):
                    path = os.path.join(LOGS_DIR, f)
                    stats = os.stat(path)
                    files.append({
                        "name": f,
                        "size": stats.st_size,
                        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x["modified"], reverse=True)
            return jsonify({"ok": True, "files": files})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/logs/files", methods=["DELETE"])
    def delete_log_files():
        """Deletes or truncates log files, handling Windows locks."""
        try:
            data = request.get_json(force=True) or {}
            target_files = data.get("files", [])
            delete_all = data.get("all", False)
            
            deleted = 0
            for f in os.listdir(LOGS_DIR):
                if f.endswith(".log") or f.endswith(".txt"):
                    if delete_all or f in target_files:
                        path = os.path.join(LOGS_DIR, f)
                        try:
                            os.remove(path)
                            deleted += 1
                        except PermissionError:
                            # File is locked (likely by Zentra Server on Windows), truncate it instead
                            try:
                                with open(path, 'w', encoding='utf-8') as fh:
                                    pass
                                deleted += 1
                            except Exception as truncate_err:
                                logger.error(f"[WebUI] Failed to truncate {f}: {truncate_err}")
                        except Exception as rm_err:
                            logger.error(f"[WebUI] Failed to delete {f}: {rm_err}")
            
            return jsonify({"ok": True, "deleted": deleted})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500


    @app.route("/api/logs/tail/<filename>")
    def tail_log_file(filename):
        """Returns the last N lines of a specific log file."""
        try:
            # Security check: prevent directory traversal
            if ".." in filename or "/" in filename or "\\" in filename:
                return jsonify({"ok": False, "error": "Invalid filename"}), 400
            
            path = os.path.join(LOGS_DIR, filename)
            if not os.path.exists(path):
                return jsonify({"ok": False, "error": "File not found"}), 404
            
            n = int(request.args.get("n", 100))
            if n > 100000: n = 100000 # Safety cap
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                return jsonify({"ok": True, "lines": lines[-n:]})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    @app.route("/api/logs/search/<filename>")
    def search_log_file(filename):
        """Searches logs for specific terms and/or times."""
        try:
            if ".." in filename or "/" in filename or "\\" in filename:
                return jsonify({"ok": False, "error": "Invalid filename"}), 400
                
            q = request.args.get("q", "").lower()
            t_filter = request.args.get("time", "").lower()
            n = int(request.args.get("n", 500))
            if n > 100000: n = 100000 # Safety cap
            
            if filename == "LIVE":
                hub = get_hub()
                results = []
                for evt in hub.history:
                    match_q = True if not q else (q in str(evt.get("text", "")).lower() or q in str(evt.get("level", "")).lower())
                    match_t = True if not t_filter else (t_filter in str(evt.get("time", "")).lower())
                    if match_q and match_t:
                        results.append(evt)
                return jsonify({"ok": True, "type": "events", "data": results[-n:]})
            else:
                path = os.path.join(LOGS_DIR, filename)
                if not os.path.exists(path):
                    return jsonify({"ok": False, "error": "File not found"}), 404
                    
                results = []
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        line_lower = line.lower()
                        match_q = True if not q else (q in line_lower)
                        match_t = True if not t_filter else (t_filter in line_lower)
                        if match_q and match_t:
                            results.append(line)
                return jsonify({"ok": True, "type": "lines", "data": results[-n:]})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/logs/raw/<filename>")
    def raw_log_file(filename):
        """Returns the entire log file as plain text."""
        try:
            if ".." in filename or "/" in filename or "\\" in filename:
                return "Invalid filename", 400
            
            path = os.path.join(LOGS_DIR, filename)
            if not os.path.exists(path):
                return "File not found", 404
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return Response(content, mimetype="text/plain")
        except Exception as e:
            return str(e), 500

    @app.route("/api/logs/stream")
    def stream_logs():
        """SSE endpoint that streams real-time log events via LogHub."""
        def generate():
            hub = get_hub()
            q = hub.subscribe()
            
            try:
                # 1. Send History (last 100 cached events)
                for evt in hub.history:
                    yield f"data: {json.dumps(evt)}\n\n"
                
                # 2. Continuous broadcast
                while True:
                    try:
                        # Wait for new log events (timeout to check for connection health)
                        evt = q.get(timeout=10)
                        yield f"data: {json.dumps(evt)}\n\n"
                    except queue.Empty:
                        # Keep-alive
                        yield ": keep-alive\n\n"
            except GeneratorExit:
                hub.unsubscribe(q)
            except Exception as e:
                logger.error(f"[WebUI] Log stream error: {e}")
                hub.unsubscribe(q)

        return Response(stream_with_context(generate()), mimetype="text/event-stream")
