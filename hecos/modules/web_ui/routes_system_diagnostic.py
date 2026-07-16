"""
routes_system_diagnostic.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — Diagnostic & Maintenance APIs
Registers:
  POST /api/system/diagnostic/full-check
  POST /api/system/diagnostic/fix-paths
  POST /api/browser/launch_external
────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify


def init_system_diagnostic_routes(app, cfg_mgr, logger):

    @app.route("/api/system/diagnostic/full-check", methods=["POST"])
    def diagnostic_full_check():
        """Runs the full Hecos setup check: Python version, dependencies, path fixes."""
        try:
            from hecos.setup.engine import check_python_version, check_dependencies, auto_fix_piper_path
            import io
            from contextlib import redirect_stdout
            output = io.StringIO()
            with redirect_stdout(output):
                check_python_version()
                check_dependencies()
                auto_fix_piper_path()
            return jsonify({"ok": True, "log": output.getvalue()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/system/diagnostic/fix-paths", methods=["POST"])
    def diagnostic_fix_paths():
        """Runs the Piper auto-fix path routine only."""
        try:
            from hecos.setup.engine import auto_fix_piper_path
            import io
            from contextlib import redirect_stdout
            output = io.StringIO()
            with redirect_stdout(output):
                auto_fix_piper_path()
            return jsonify({"ok": True, "log": output.getvalue()})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
