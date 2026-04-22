"""
MODULE: Remote Triggers Backend - Zentra Core
DESCRIPTION: HTTP endpoints to trigger PTT and manage ptt_sources config.
             Enables smartwatch / webhook / external hardware PTT activation.

ROUTES:
  GET  /api/remote-triggers/status          — bus status (active sources, ptt_active)
  GET  /api/remote-triggers/ptt/start       — fire_ptt("start", "webhook")
  GET  /api/remote-triggers/ptt/stop        — fire_ptt("stop", "webhook")
  GET  /api/remote-triggers/ptt/toggle      — fire_ptt("toggle", "webhook")
  GET  /api/remote-triggers/config          — read ptt_sources from audio.yaml
  POST /api/remote-triggers/config          — write ptt_sources to audio.yaml + reload bus
"""

from flask import request, jsonify


def init_remote_trigger_routes(app, logger, get_sm=None):
    def _sm():
        return get_sm() if callable(get_sm) else get_sm

    # ── BUS STATUS ────────────────────────────────────────────────────────────

    @app.route("/api/remote-triggers/status", methods=["GET"])
    def rt_status():
        """Returns current PTT Bus status."""
        try:
            from zentra.core.audio import ptt_bus
            return jsonify({"ok": True, **ptt_bus.get_status()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── PTT FIRE ENDPOINTS ───────────────────────────────────────────────────

    @app.route("/api/remote-triggers/ptt/start", methods=["GET", "POST"])
    def rt_ptt_start():
        """Activates PTT (push-to-talk recording)."""
        try:
            from zentra.core.audio import ptt_bus
            active = ptt_bus.fire_ptt("start", "webhook")
            logger.info("[RemoteTriggers] PTT START via webhook.")
            return jsonify({"ok": True, "ptt_active": active})
        except Exception as e:
            logger.error(f"[RemoteTriggers] ptt/start error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/remote-triggers/ptt/stop", methods=["GET", "POST"])
    def rt_ptt_stop():
        """Deactivates PTT."""
        try:
            from zentra.core.audio import ptt_bus
            active = ptt_bus.fire_ptt("stop", "webhook")
            logger.info("[RemoteTriggers] PTT STOP via webhook.")
            return jsonify({"ok": True, "ptt_active": active})
        except Exception as e:
            logger.error(f"[RemoteTriggers] ptt/stop error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/remote-triggers/ptt/toggle", methods=["GET", "POST"])
    def rt_ptt_toggle():
        """Toggles PTT state."""
        try:
            from zentra.core.audio import ptt_bus
            active = ptt_bus.fire_ptt("toggle", "webhook")
            logger.info(f"[RemoteTriggers] PTT TOGGLE via webhook → {active}")
            return jsonify({"ok": True, "ptt_active": active})
        except Exception as e:
            logger.error(f"[RemoteTriggers] ptt/toggle error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── SOURCES CONFIG ────────────────────────────────────────────────────────

    @app.route("/api/remote-triggers/config", methods=["GET"])
    def rt_get_config():
        """Returns ptt_sources configuration and custom_ptt_key."""
        try:
            from zentra.core.audio.device_manager import get_audio_config
            cfg = get_audio_config()
            return jsonify({
                "ok": True,
                "ptt_sources":    cfg.get("ptt_sources", {}),
                "custom_ptt_key": cfg.get("custom_ptt_key", ""),
                "ptt_hotkey":     cfg.get("ptt_hotkey", "ctrl+shift"),
            })
        except Exception as e:
            logger.error(f"[RemoteTriggers] GET config error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/remote-triggers/config", methods=["POST"])
    def rt_post_config():
        """
        Saves ptt_sources and/or custom_ptt_key then reloads the PTT Bus.
        Payload: { ptt_sources: {...}, custom_ptt_key: "..." }
        """
        try:
            data = request.get_json(force=True) or {}
            from zentra.core.audio.device_manager import get_audio_config, _save_audio_config
            cfg = get_audio_config()

            if "ptt_sources" in data:
                existing = cfg.get("ptt_sources", {})
                existing.update(data["ptt_sources"])
                cfg["ptt_sources"] = existing

            if "custom_ptt_key" in data:
                cfg["custom_ptt_key"] = data["custom_ptt_key"].strip()

            if "ptt_hotkey" in data:
                cfg["ptt_hotkey"] = data["ptt_hotkey"].strip()

            _save_audio_config(cfg)

            # Reload the PTT Bus with new settings
            sm = _sm()
            from zentra.core.audio import ptt_bus
            ptt_bus.reload(state=sm)

            logger.info(f"[RemoteTriggers] Config saved and bus reloaded. sources={cfg.get('ptt_sources')}")
            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[RemoteTriggers] POST config error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
