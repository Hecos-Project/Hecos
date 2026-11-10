"""
Telemetry Widget — WEB_UI Sidebar Extension
Provides its own autonomous REST API for reading and saving widget config (track_cpu/ram/vram)
to the package's own telemetry_widget.toml — zero dependency on core plugins.yaml.
"""
from flask import jsonify, request
try:
    from hecos.core.logging import logger
except ImportError:
    class _L:
        def debug(self, *a): pass
        def info(self, *a): pass
        def error(self, *a): pass
    logger = _L()

try:
    from .config_manager import get_config, save_config
except ImportError:
    try:
        from config_manager import get_config, save_config
    except ImportError:
        def get_config(): return type('C', (), {'track_cpu': False, 'track_ram': False, 'track_vram': False})()
        def save_config(d): return False


def init_routes(app, root_dir: str = None):
    logger.debug("TelemetryWidget", "Telemetry sidebar dashboard widget loaded.")

    @app.route("/api/telemetry_widget/config", methods=["GET"])
    def telemetry_widget_get_config():
        """Returns the current hardware monitoring settings from the package\'s own TOML."""
        try:
            cfg = get_config()
            return jsonify({
                "ok": True,
                "track_cpu":  cfg.track_cpu,
                "track_ram":  cfg.track_ram,
                "track_vram": cfg.track_vram,
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/telemetry_widget/config", methods=["POST"])
    def telemetry_widget_save_config():
        """Saves hardware monitoring toggles to the package\'s own TOML. No core YAML involved."""
        try:
            data = request.get_json(force=True) or {}
            ok = save_config(data)
            return jsonify({"ok": ok})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
