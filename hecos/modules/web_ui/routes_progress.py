"""
hecos/modules/web_ui/routes_progress.py
─────────────────────────────────────────────────────────────────────────────
WebUI routes for tracking and managing unified system progress tasks.
Endpoints:
  GET  /api/progress/active       → list active tasks and recent completed tasks
  GET  /api/progress/<task_id>    → specific task status
  POST /api/progress/<task_id>/cancel → cancel a running task
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from flask import jsonify, request
from hecos.core.progress import get_progress_manager


def init_progress_routes(app, logger):
    logger.info("[WebUI] Registering unified progress routes...")

    @app.route("/api/progress/active", methods=["GET"])
    def get_active_progress():
        """Returns all currently active and recently completed progress tasks."""
        try:
            pm = get_progress_manager()
            active = pm.list_active()
            recent = pm.list_recent(limit=10)
            return jsonify({
                "ok": True,
                "active": active,
                "recent": recent,
            })
        except Exception as exc:
            logger.error(f"[WebUI] Error getting active progress: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/progress/<task_id>", methods=["GET"])
    def get_task_progress(task_id: str):
        """Returns the current state of a specific task."""
        try:
            pm = get_progress_manager()
            task = pm.get_task(task_id)
            if not task:
                return jsonify({"ok": False, "error": "Task non trovato"}), 404
            return jsonify({"ok": True, "task": task.to_dict()})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/progress/<task_id>/cancel", methods=["POST"])
    def cancel_task_progress(task_id: str):
        """Requests cancellation of a running task."""
        try:
            body = request.get_json(silent=True) or {}
            reason = body.get("reason", "Annullato dall'utente.")
            pm = get_progress_manager()
            ok = pm.cancel_task(task_id, reason=reason)
            if ok:
                logger.info(f"[WebUI] Task '{task_id}' cancellation requested.")
                return jsonify({"ok": True, "message": "Annullamento richiesto."})
            else:
                return jsonify({
                    "ok": False,
                    "error": "Impossibile annullare il task (non trovato o già terminato)."
                }), 400
        except Exception as exc:
            logger.error(f"[WebUI] Error cancelling task '{task_id}': {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    @app.route("/api/progress/demo", methods=["POST"])
    def trigger_demo_progress():
        """Simulates a real multi-phase progress task to test WebUI and Presenter live."""
        import threading
        import time

        def _run_demo():
            from hecos.core.progress import progress
            phases = [
                ("download", 40.0, "Download files"),
                ("deps", 40.0, "Installing dependencies"),
                ("verify", 20.0, "System verification"),
            ]
            total_bytes = 45 * 1024 * 1024  # 45 MB
            chunk = 3 * 1024 * 1024        # 3 MB per tick

            with progress.task("demo_task", "Demo Installation", source="DEMO", phases=phases) as t:
                # Phase 1: Download
                t.phase("download", message="Downloading assets...")
                done = 0
                while done < total_bytes:
                    t.check_cancelled()
                    time.sleep(0.3)
                    done = min(total_bytes, done + chunk)
                    t.advance(bytes_done=done, total_bytes=total_bytes)

                # Phase 2: Pip installation
                t.phase("deps", message="Installing pip dependencies...")
                pip_samples = [
                    "Collecting torch>=2.2.0",
                    "Downloading torch-2.2.0-cp312-win_amd64.whl (18.4 MB)",
                    "Installing collected packages: torch",
                    "Successfully installed torch-2.2.0"
                ]
                for p_msg in pip_samples:
                    t.check_cancelled()
                    time.sleep(0.6)
                    t.advance(message=p_msg, log=p_msg)

                # Phase 3: Finalize
                t.phase("verify", message="Final check and registration...")
                time.sleep(0.8)
                t.done("Installation completed successfully (100%)!")

        t = threading.Thread(target=_run_demo, daemon=True)
        t.start()
        return jsonify({"ok": True, "message": "Demo progress started.", "task_id": "demo_task"})
