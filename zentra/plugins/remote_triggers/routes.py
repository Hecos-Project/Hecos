"""
Plugin: Remote Triggers — Routes
HTTP Webhook endpoints for external hardware triggers (Arduino, ESP32, USB buttons).
"""

import sys
from flask import Blueprint, jsonify, request

try:
    from core.logging import logger
except ImportError:
    class _DL:
        def info(self, *a, **k): print("[RT]", *a)
        def debug(self, *a, **k): pass
        def error(self, *a, **k): print("[RT ERR]", *a)
    logger = _DL()

# ── Blueprint ────────────────────────────────────────────────────────────────
rt_bp = Blueprint(
    "remote_triggers",
    __name__,
    static_folder="static",
    static_url_path="/remote_triggers_static"
)

# ── Shared SSE queue injected by web_ui server ────────────────────────────
# When the web_ui registers routes it will call inject_sse_queue()
_sse_queue_getter = None


def inject_sse_queue(getter_fn):
    """Called by init_remote_triggers_routes to provide access to the SSE event queue."""
    global _sse_queue_getter
    _sse_queue_getter = getter_fn


def _push_event(event_type: str, data: dict):
    """
    Pushes an event into the WebUI SSE stream so the browser picks it up.
    Falls back to a no-op if the queue is unavailable.
    """
    if _sse_queue_getter is None:
        logger.debug("[RT] SSE queue not configured yet, event dropped.")
        return
    try:
        q = _sse_queue_getter()
        if q:
            import json
            q.put(json.dumps({"type": event_type, **data}))
    except Exception as e:
        logger.error(f"[RT] Failed to push SSE event: {e}")


# ── Routes ────────────────────────────────────────────────────────────────────

@rt_bp.route("/api/remote-triggers/status", methods=["GET"])
def rt_status():
    """Health check — confirms the plugin is active."""
    return jsonify({
        "ok": True,
        "plugin": "remote_triggers",
        "version": "1.0.0",
        "message": "Remote Triggers online. Waiting for hardware signals."
    })


@rt_bp.route("/api/remote-triggers/ptt/start", methods=["GET", "POST"])
def rt_ptt_start():
    """
    Webhook: START listening (PTT pressed).
    Call this from your Arduino/ESP32/USB button when the button is pressed DOWN.
    
    GET  /api/remote-triggers/ptt/start
    POST /api/remote-triggers/ptt/start  (body optional)
    """
    logger.info("[RT] Webhook received: PTT START")
    _push_event("remote_ptt", {"action": "start"})
    return jsonify({"ok": True, "action": "ptt_start"})


@rt_bp.route("/api/remote-triggers/ptt/stop", methods=["GET", "POST"])
def rt_ptt_stop():
    """
    Webhook: STOP listening (PTT released).
    Call this from your Arduino/ESP32/USB button when the button is RELEASED.
    
    GET  /api/remote-triggers/ptt/stop
    POST /api/remote-triggers/ptt/stop  (body optional)
    """
    logger.info("[RT] Webhook received: PTT STOP")
    _push_event("remote_ptt", {"action": "stop"})
    return jsonify({"ok": True, "action": "ptt_stop"})


@rt_bp.route("/api/remote-triggers/ptt/toggle", methods=["GET", "POST"])
def rt_ptt_toggle():
    """
    Webhook: TOGGLE PTT (single press/release cycle).
    Useful for buttons that don't distinguish press/release.
    
    GET  /api/remote-triggers/ptt/toggle
    POST /api/remote-triggers/ptt/toggle
    """
    logger.info("[RT] Webhook received: PTT TOGGLE")
    _push_event("remote_ptt", {"action": "toggle"})
    return jsonify({"ok": True, "action": "ptt_toggle"})


# ── Init function ─────────────────────────────────────────────────────────────

def init_remote_triggers_routes(app, logger_instance=None, sse_queue_getter=None):
    """Registers the Remote Triggers Blueprint on the Flask app."""
    _log = logger_instance or logger
    
    if sse_queue_getter:
        inject_sse_queue(sse_queue_getter)
    
    if "remote_triggers" not in app.blueprints:
        app.register_blueprint(rt_bp)
        _log.info("[RemoteTriggers] Blueprint 'remote_triggers' registered.")
    else:
        _log.debug("[RemoteTriggers] Blueprint already registered.")
