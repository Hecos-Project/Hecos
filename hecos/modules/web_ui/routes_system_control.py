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
            while True:
                sm_live = _sm()
                if sm_live:
                    events = sm_live.pop_events()
                    for ev in events:
                        out_ev = {"type": ev.get("type")}
                        data   = ev.get("data")
                        if isinstance(data, dict):
                            out_ev.update(data)
                        elif data is not None:
                            out_ev["data"] = data
                        yield f"data: {json.dumps(out_ev)}\n\n"
                time.sleep(0.1)

        return Response(stream_with_context(generate()), mimetype="text/event-stream")
