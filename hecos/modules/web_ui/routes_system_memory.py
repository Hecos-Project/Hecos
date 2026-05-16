"""
routes_system_memory.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Memory Management APIs
Registers:
  POST /api/memory/clear
  GET  /api/memory/status
────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify, request


def init_system_memory_routes(app, cfg_mgr, logger):

    @app.route("/api/memory/clear", methods=["POST"])
    def memory_clear():
        """Wipes the episodic history from the DB (optionally granular)."""
        try:
            data = request.get_json(force=True) or {}
            days = data.get("days") if data.get("days") != "all" else None
            if days is not None:
                try: days = int(days)
                except: days = None

            from hecos.memory.brain_interface import clear_history
            cleared = clear_history(days=days)
            if cleared:
                msg = f"History cleared (days={days if days else 'all'})."
                logger.info(f"[WebUI] {msg}")
                return jsonify({"ok": True, "message": msg})
            return jsonify({"ok": False, "error": "Failed to clear."}), 500
        except Exception as exc:
            logger.error(f"[WebUI] memory_clear error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/memory/status", methods=["GET"])
    def memory_status():
        """Returns memory row count and cognition config."""
        try:
            from hecos.memory.brain_interface import get_memory_stats
            stats = get_memory_stats()
            cog   = cfg_mgr.config.get("cognition", {})
            return jsonify({
                "ok": True,
                "total_messages": stats.get("total_messages", 0),
                "cognition": cog,
            })
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500
