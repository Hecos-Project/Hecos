from flask import jsonify

try:
    from hecos.core.logging import logger
    # Hook directly into the living backend instance of the weather plugin
    from hecos.plugins.weather.main import tools as weather_tools
except ImportError:
    weather_tools = None

import os
from flask import send_from_directory

def init_routes(app):
    """Registers the isolated API routes for the Weather Widget."""
    
    _static_dir = os.path.join(os.path.dirname(__file__), "static")
    
    @app.route("/ext/weather_widget/static/<path:filename>")
    def weather_widget_static(filename):
        return send_from_directory(_static_dir, filename)
    
    @app.route("/api/widgets/weather", methods=["GET"])
    def get_weather_widget_data():
        if weather_tools:
            data = weather_tools.get_weather_data()
            if "error" not in data:
                return jsonify({"ok": True, "data": data})
            return jsonify({"ok": False, "error": data["error"]})
        return jsonify({"ok": False, "error": "Weather backend plugin not loaded."})
