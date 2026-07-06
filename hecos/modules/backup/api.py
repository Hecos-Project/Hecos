"""
MODULE: Backup API
DESCRIPTION: Flask routes for the Global Backup Orchestrator.
             All endpoints are under /hecos/api/backup/
"""

import io
import json
import os
import threading
from datetime import datetime, timezone
from flask import request, jsonify, send_file
from hecos.core.logging import logger

_backup_in_progress = False
_backup_lock = threading.Lock()


def register_routes(app) -> None:
    """Register all backup API routes on the Flask app."""

    from hecos.modules.backup import store as bstore
    from hecos.modules.backup import scheduler as bscheduler

    # ── GET /hecos/api/backup/config ─────────────────────────────────────────
    @app.route("/hecos/api/backup/config", methods=["GET"])
    def backup_get_config():
        """Return current backup configuration and metadata."""
        try:
            cfg = bstore.load()
            cfg["presets"] = bstore.SCHEDULE_PRESETS

            from hecos.modules.backup.orchestrator import get_backup_metadata
            modules_meta = get_backup_metadata()

            return jsonify({"ok": True, "config": cfg, "modules_meta": modules_meta})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── PUT /hecos/api/backup/config ─────────────────────────────────────────
    @app.route("/hecos/api/backup/config", methods=["PUT"])
    def backup_put_config():
        """Save backup configuration. Reschedules if schedule changed."""
        try:
            data = request.get_json(force=True) or {}
            cfg = bstore.load()

            # Update fields
            for field in ("enabled", "schedule_preset", "schedule_cron",
                          "destination", "keep_last", "modules"):
                if field in data:
                    cfg[field] = data[field]

            # Sync cron from preset if not custom
            preset = cfg.get("schedule_preset", "daily_2am")
            if preset != "custom":
                cfg["schedule_cron"] = bstore.get_cron_for_preset(preset)

            bstore.save(cfg)

            # Live-update scheduler
            if cfg.get("enabled") and cfg.get("schedule_cron"):
                bscheduler.reschedule(cfg["schedule_cron"])
            else:
                bscheduler.reschedule(None)

            return jsonify({"ok": True})
        except Exception as e:
            logger.error(f"[BACKUP API] PUT /config error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET /hecos/api/backup/status ─────────────────────────────────────────
    @app.route("/hecos/api/backup/status", methods=["GET"])
    def backup_get_status():
        """Return scheduler status and last run info."""
        try:
            status = bscheduler.get_status()
            status["in_progress"] = _backup_in_progress
            return jsonify({"ok": True, "status": status})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /hecos/api/backup/run ───────────────────────────────────────────
    @app.route("/hecos/api/backup/run", methods=["POST"])
    def backup_run_now():
        """Trigger a full backup immediately. Runs in background thread."""
        global _backup_in_progress

        with _backup_lock:
            if _backup_in_progress:
                return jsonify({"ok": False, "error": "A backup is already running."}), 409
            _backup_in_progress = True

        def _do_backup():
            global _backup_in_progress
            try:
                from hecos.modules.backup.orchestrator import run_full_backup
                cfg = bstore.load()
                dest = cfg.get("destination", "")
                modules_enabled = cfg.get("modules", {})
                result = run_full_backup(app, dest, modules_enabled)
                ts = datetime.now(timezone.utc).isoformat()
                outcome = "ok" if result.get("ok") else "error"
                bstore.update_last_run(outcome, ts)
                _cleanup_old_backups(dest, cfg.get("keep_last", 7))
            except Exception as e:
                logger.error(f"[BACKUP API] Background backup error: {e}")
            finally:
                _backup_in_progress = False

        threading.Thread(target=_do_backup, daemon=True, name="hecos-backup").start()
        return jsonify({"ok": True, "message": "Backup started in background"})

    # ── POST /hecos/api/backup/run/<module> ──────────────────────────────────
    @app.route("/hecos/api/backup/run/<module_name>", methods=["POST"])
    def backup_run_module(module_name: str):
        """Trigger backup of a single module. Returns ZIP download."""
        try:
            from hecos.modules.backup.orchestrator import backup_single_module
            data = backup_single_module(app, module_name)
            if not data or data.get("ok") is False:
                return jsonify({"ok": False, "error": data.get("error", "Backup failed")}), 500

            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"hecos_{module_name}_{ts}.json"
            buf = io.BytesIO(json.dumps(data, indent=2, ensure_ascii=False).encode())
            return send_file(buf, download_name=filename,
                             as_attachment=True, mimetype="application/json")
        except Exception as e:
            logger.error(f"[BACKUP API] run/{module_name} error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── GET /hecos/api/backup/history ────────────────────────────────────────
    @app.route("/hecos/api/backup/history", methods=["GET"])
    def backup_get_history():
        """List backup ZIP files in the configured destination folder."""
        try:
            cfg = bstore.load()
            dest = cfg.get("destination", "")
            if not dest or not os.path.isdir(dest):
                return jsonify({"ok": True, "files": []})

            files = []
            for fname in sorted(os.listdir(dest), reverse=True):
                if fname.startswith("hecos_backup_") and fname.endswith(".zip"):
                    fpath = os.path.join(dest, fname)
                    stat = os.stat(fpath)
                    files.append({
                        "filename": fname,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    })
            return jsonify({"ok": True, "files": files})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── DELETE /hecos/api/backup/history/<filename> ──────────────────────────
    @app.route("/hecos/api/backup/history/<filename>", methods=["DELETE"])
    def backup_delete_file(filename: str):
        """Delete a backup ZIP from the history folder."""
        try:
            cfg = bstore.load()
            dest = cfg.get("destination", "")
            if not dest:
                return jsonify({"ok": False, "error": "No destination configured"}), 400

            # Security: only allow files starting with hecos_backup_
            if not filename.startswith("hecos_backup_") or not filename.endswith(".zip"):
                return jsonify({"ok": False, "error": "Invalid filename"}), 400

            fpath = os.path.join(dest, filename)
            if not os.path.exists(fpath):
                return jsonify({"ok": False, "error": "File not found"}), 404

            os.remove(fpath)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /hecos/api/backup/download/<filename> ───────────────────────────
    @app.route("/hecos/api/backup/download/<filename>", methods=["GET"])
    def backup_download_file(filename: str):
        """Download a backup ZIP by filename."""
        try:
            cfg = bstore.load()
            dest = cfg.get("destination", "")
            if not dest or not filename.endswith(".zip"):
                return jsonify({"ok": False, "error": "Invalid request"}), 400
            fpath = os.path.join(dest, filename)
            if not os.path.exists(fpath):
                return jsonify({"ok": False, "error": "File not found"}), 404
            return send_file(fpath, as_attachment=True, mimetype="application/zip")
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── POST /hecos/api/backup/restore ───────────────────────────────────────
    @app.route("/hecos/api/backup/restore", methods=["POST"])
    def backup_restore():
        """
        Restore from a ZIP.
        Supports:
          - multipart/form-data with 'file' field (upload)
          - JSON body with { filename: "...", modules: ["calendar", ...] }
            to restore from history (by filename in dest folder)
        """
        try:
            from hecos.modules.backup.orchestrator import restore_from_zip
            cfg = bstore.load()

            # Determine source of ZIP bytes
            if "file" in request.files:
                zip_bytes = request.files["file"].read()
                modules = request.form.getlist("modules") or None
            else:
                body = request.get_json(force=True) or {}
                fname = body.get("filename", "")
                modules = body.get("modules") or None

                if not fname:
                    return jsonify({"ok": False, "error": "filename required"}), 400

                dest = cfg.get("destination", "")
                fpath = os.path.join(dest, fname)
                if not os.path.exists(fpath):
                    return jsonify({"ok": False, "error": "Backup file not found"}), 404

                with open(fpath, "rb") as f:
                    zip_bytes = f.read()

            result = restore_from_zip(app, zip_bytes, modules)
            return jsonify(result)

        except Exception as e:
            logger.error(f"[BACKUP API] /restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    logger.info("BACKUP", "✅ Backup API routes registered.")


# ── Cleanup helper ────────────────────────────────────────────────────────────

def _cleanup_old_backups(dest: str, keep_last: int) -> None:
    """Delete oldest backup ZIPs if count exceeds keep_last."""
    if not dest or not os.path.isdir(dest) or keep_last <= 0:
        return
    try:
        files = sorted(
            [f for f in os.listdir(dest)
             if f.startswith("hecos_backup_") and f.endswith(".zip")]
        )
        to_delete = files[:-keep_last] if len(files) > keep_last else []
        for fname in to_delete:
            os.remove(os.path.join(dest, fname))
            logger.info("BACKUP", f"Deleted old backup: {fname}")
    except Exception as e:
        logger.warning("BACKUP", f"Cleanup error: {e}")
