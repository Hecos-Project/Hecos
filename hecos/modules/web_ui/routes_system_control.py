"""
routes_system_control.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — System / Generation Control APIs
Registers:
  GET  /api/system/payload
  POST /api/system/stop
  GET  /api/events          (SSE)
────────────────────────────────────────────────────────────────────────────
"""
import json
import time
from flask import jsonify, request, Response, stream_with_context


def init_system_control_routes(app, logger, get_sm):

    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    @app.route("/api/system/payload", methods=["GET"])
    def get_system_payload():
        """Returns the last LLM payload sizes for context usage optimization."""
        try:
            from hecos.core.llm.client import LAST_PAYLOAD_INFO
            return jsonify({"ok": True, "payload": LAST_PAYLOAD_INFO})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/system/stop", methods=["POST"])
    def system_stop():
        """Interrupts any ongoing backend generation (Console/Voice input)."""
        try:
            sm = _sm()
            if sm:
                sm.webui_stop_requested = True
            logger.info("[WebUI] User requested generation stop.")
            return jsonify({"ok": True, "message": "Stop requested."})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/events")
    def stream_events():
        """SSE endpoint: pushes state-manager events to the browser."""
        def generate():
            sm_live = _sm()
            if not sm_live:
                return

            # Check in a dedicated queue for this SSE connection
            q = sm_live.check_in()
            try:
                while True:
                    import queue
                    try:
                        # Blocking wait for the next event, max 1 second to allow graceful shutdown checks
                        ev = q.get(timeout=1.0)
                        out_ev = {"type": ev.get("type")}
                        data   = ev.get("data")
                        if isinstance(data, dict):
                            out_ev.update(data)
                        elif data is not None:
                            out_ev["data"] = data
                        yield f"data: {json.dumps(out_ev)}\n\n"
                    except queue.Empty:
                        # Yield a keep-alive comment to prevent browser from terminating idle connection
                        yield ": keep-alive\n\n"
            except GeneratorExit:
                # Browser disconnected
                pass
            finally:
                sm_live.check_out(q)

        return Response(stream_with_context(generate()), mimetype="text/event-stream")
