"""
weather_pro_widget — WEB_UI Extension
Registers the /api/weather_pro/data route used by the widget iframe.
Delegates all data fetching to the WEATHER_PRO plugin instance.
"""
from flask import jsonify, request
from flask_login import login_required


def init_routes(app):

    @app.route("/api/weather_pro/data", methods=["GET"])
    @login_required
    def api_weather_pro_data():
        """
        Returns current weather + 7-day forecast as JSON.
        Query param: ?city=Rome   (optional, falls back to user profile / IP)
        """
        city = request.args.get("city", "").strip()

        # Reach the WEATHER_PRO plugin via the module_state registry
        try:
            from hecos.core.system.module_state import get_plugin_module
            plugin_module = get_plugin_module("WEATHER_PRO")

            if plugin_module is None:
                # Try legacy (has info() + tools attribute)
                from hecos.core.system.module_state import _loaded_plugins
                plugin_module = _loaded_plugins.get("WEATHER_PRO")

            if plugin_module is None:
                return jsonify({"error": "WEATHER_PRO plugin is not active. Enable it in the Package Manager."}), 503

            # Class-based plugins expose their instance as `.tools`
            instance = getattr(plugin_module, "tools", None)
            if instance is None:
                return jsonify({"error": "WEATHER_PRO plugin has no tools instance."}), 500

            data = instance.get_weather_data(city)
            return jsonify(data)

        except Exception as e:
            return jsonify({"error": str(e)}), 500
