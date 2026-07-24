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

    # ── External Dependencies (EDM) APIs ──────────────────────────────────────

    @app.route("/api/ext_deps", methods=["GET"])
    def get_ext_deps():
        """Returns the status of all known external dependencies."""
        try:
            from hecos.core.ext_deps import get_status_all
            return jsonify({"ok": True, "deps": get_status_all()})
        except ImportError:
            return jsonify({"ok": False, "error": "EDM module not available"}), 501
        except Exception as e:
            logger.error(f"[EDM API] Error listing deps: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/ext_deps/<dep_id>/status", methods=["GET"])
    def get_ext_dep_status(dep_id):
        """Returns the installation status of a specific dependency."""
        try:
            from hecos.core.ext_deps import is_installed
            installed = is_installed(dep_id)
            return jsonify({"ok": True, "installed": installed})
        except ImportError:
            return jsonify({"ok": False, "error": "EDM module not available"}), 501
        except Exception as e:
            logger.error(f"[EDM API] Error checking status for {dep_id}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/ext_deps/<dep_id>/install", methods=["POST"])
    def install_ext_dep(dep_id):
        """Triggers the async background installation of a dependency."""
        try:
            from hecos.core.ext_deps import install_dep_async
            
            def _on_done(success, message):
                logger.info(f"[EDM API] Async install for {dep_id} finished. Success: {success}, msg: {message}")

            install_dep_async(dep_id, on_done=_on_done)
            return jsonify({"ok": True, "message": f"Installation of {dep_id} started in background."})
        except ImportError:
            return jsonify({"ok": False, "error": "EDM module not available"}), 501
        except Exception as e:
            logger.error(f"[EDM API] Error starting install for {dep_id}: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
