"""
map_widget/main.py
─────────────────────────────────────────────────────────────────────────────
Hecos WebUI Extension — GPS Map Widget
Registers the Flask API routes used by the map widget frontend.
─────────────────────────────────────────────────────────────────────────────
"""
import os
from flask import jsonify, send_from_directory

try:
    from hecos.core.logging import logger
    from hecos.plugins.map.main import tools as map_tools
except ImportError:
    map_tools = None
    logger = None


def init_routes(app):
    """Registers the isolated API routes for the Map Widget."""

    _static_dir = os.path.join(os.path.dirname(__file__), "static")

    @app.route("/ext/map_widget/static/<path:filename>")
    def map_widget_static(filename):
        return send_from_directory(_static_dir, filename)

    @app.route("/api/widgets/map/home", methods=["GET"])
    def get_map_home_data():
        """
        Returns the geocoded home location from the user profile.
        Response: { ok: true, lat: float, lon: float, display_name: str }
        """
        if not map_tools:
            return jsonify({"ok": False, "error": "Plugin MAP non disponibile."}), 503

        try:
            result = map_tools.get_home_location(username="admin")
            if "error" in result:
                return jsonify({"ok": False, "error": result["error"]})
            return jsonify({
                "ok": True,
                "lat": result["lat"],
                "lon": result["lon"],
                "display_name": result.get("display_name", ""),
                "query": result.get("query", "")
            })
        except Exception as e:
            if logger:
                logger.warning(f"[map_widget] /api/widgets/map/home error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/widgets/map/geocode", methods=["GET"])
    def get_map_geocode():
        """
        Geocodes an arbitrary query string.
        Query param: ?q=Rome%2C+Italy
        Response: { ok: true, lat: float, lon: float, display_name: str }
        """
        from flask import request as flask_request
        q = flask_request.args.get("q", "").strip()
        if not q:
            return jsonify({"ok": False, "error": "Missing query param 'q'"}), 400

        if not map_tools:
            return jsonify({"ok": False, "error": "Plugin MAP non disponibile."}), 503

        try:
            result = map_tools.geocode(q)
            if "error" in result:
                return jsonify({"ok": False, "error": result["error"]})
            return jsonify({
                "ok": True,
                "lat": result["lat"],
                "lon": result["lon"],
                "display_name": result.get("display_name", q)
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
