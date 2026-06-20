"""
MODULE: Module Backup Routes
DESCRIPTION: Aggiunge le rotte /backup e /restore a tutti i moduli Hecos
             che non le hanno nativamente. Registrate via server_flask.py.

Route aggiunge:
  GET  /api/calendar/backup          → Export eventi calendario (JSON)
  POST /api/calendar/restore         → Import eventi calendario
  GET  /api/reminders/backup         → Export promemoria (JSON)
  POST /api/reminders/restore        → Import promemoria
  GET  /hecos/api/history/backup     → Export sessioni chat (JSON)
  POST /hecos/api/history/restore    → Import sessioni chat
  GET  /hecos/api/memory/backup      → Export episodic memory (JSON)
  POST /hecos/api/memory/restore     → Import episodic memory
  GET  /api/flows/backup             → Export tutti i flow (JSON)
  POST /api/flows/restore            → Import flow da JSON
  GET  /hecos/api/users/backup       → Export utenti/profili (JSON)
  POST /hecos/api/users/restore      → Import utenti
"""

from flask import jsonify, request
from hecos.core.logging import logger


def register_module_backup_routes(app) -> None:
    """Registra tutte le rotte /backup e /restore sui moduli che ne sono privi."""

    # ═══════════════════════════════════════════════════════════════════════════
    # CALENDAR
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/api/calendar/backup", methods=["GET"], endpoint="mbkp_calendar_backup")
    def calendar_backup():
        """Esporta tutti gli eventi del calendario come JSON."""
        try:
            from hecos.plugins.calendar import store
            with store._get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM calendar_events ORDER BY start_iso ASC"
                ).fetchall()
            events = [dict(r) for r in rows]
            return jsonify({"ok": True, "count": len(events), "data": events})
        except Exception as e:
            logger.error(f"[BACKUP] calendar_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/calendar/restore", methods=["POST"], endpoint="mbkp_calendar_restore")
    def calendar_restore():
        """
        Ripristina eventi calendario da JSON.
        Body: { data: [...], mode: "duplicate"|"replace" }
        """
        try:
            from hecos.plugins.calendar import store
            import uuid as _uuid
            from datetime import datetime as _dt

            body = request.get_json(force=True) or {}
            events = body.get("data", [])
            mode   = body.get("mode", "duplicate")

            if not isinstance(events, list):
                return jsonify({"ok": False, "error": "data must be a list"}), 400

            with store._get_conn() as conn:
                if mode == "replace":
                    conn.execute("DELETE FROM calendar_events")

                imported = 0
                for ev in events:
                    try:
                        new_id = str(_uuid.uuid4())
                        conn.execute(
                            """INSERT OR IGNORE INTO calendar_events
                               (id, title, start_iso, end_iso, all_day, color, notes,
                                linked_reminder_id, interactive, external_id, sync_source, created_at)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (
                                new_id,
                                ev.get("title", "Evento"),
                                ev.get("start_iso", ""),
                                ev.get("end_iso"),
                                int(ev.get("all_day", 0)),
                                ev.get("color"),
                                ev.get("notes"),
                                ev.get("linked_reminder_id"),
                                int(ev.get("interactive", 0)),
                                ev.get("external_id"),
                                ev.get("sync_source"),
                                ev.get("created_at") or _dt.now().isoformat(),
                            )
                        )
                        imported += 1
                    except Exception as row_e:
                        logger.error(f"[BACKUP] calendar row error: {row_e}")

            return jsonify({"ok": True, "imported": imported})
        except Exception as e:
            logger.error(f"[BACKUP] calendar_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════
    # REMINDERS
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/api/reminders/backup", methods=["GET"], endpoint="mbkp_reminders_backup")
    def reminders_backup():
        """Esporta tutti i promemoria come JSON."""
        try:
            from hecos.plugins.reminder import store
            reminders = store.get_all()
            return jsonify({"ok": True, "count": len(reminders), "data": reminders})
        except Exception as e:
            logger.error(f"[BACKUP] reminders_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/api/reminders/restore", methods=["POST"], endpoint="mbkp_reminders_restore")
    def reminders_restore():
        """
        Ripristina promemoria da JSON.
        Body: { data: [...], mode: "duplicate"|"replace" }
        """
        try:
            from hecos.plugins.reminder import store
            body = request.get_json(force=True) or {}
            reminders = body.get("data", [])
            mode = body.get("mode", "duplicate")

            if not isinstance(reminders, list):
                return jsonify({"ok": False, "error": "data must be a list"}), 400

            count = store.import_reminders(reminders, mode=mode)
            return jsonify({"ok": True, "imported": count})
        except Exception as e:
            logger.error(f"[BACKUP] reminders_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════
    # CHAT HISTORY (sessioni)
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/hecos/api/history/backup", methods=["GET"], endpoint="mbkp_history_backup")
    def history_backup():
        """Esporta tutte le sessioni chat e i relativi messaggi come JSON."""
        try:
            from hecos.memory import session_manager
            import sqlite3

            db_path = session_manager.PATH_DB
            if not __import__("os").path.exists(db_path):
                return jsonify({"ok": True, "count": 0, "data": []})

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                sessions = [dict(r) for r in conn.execute(
                    "SELECT * FROM sessions ORDER BY created_at ASC"
                ).fetchall()]

                # Attach messages to each session
                for s in sessions:
                    msgs = conn.execute(
                        "SELECT * FROM history WHERE session_id = ? ORDER BY id ASC",
                        (s["id"],)
                    ).fetchall()
                    s["messages"] = [dict(m) for m in msgs]

            return jsonify({"ok": True, "count": len(sessions), "data": sessions})
        except Exception as e:
            logger.error(f"[BACKUP] history_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/history/restore", methods=["POST"], endpoint="mbkp_history_restore")
    def history_restore():
        """
        Ripristina sessioni chat da JSON.
        Body: { data: [...sessions...], mode: "duplicate"|"replace" }
        """
        try:
            from hecos.memory import session_manager
            import sqlite3, uuid as _uuid
            from datetime import datetime as _dt

            body = request.get_json(force=True) or {}
            sessions = body.get("data", [])
            mode = body.get("mode", "duplicate")

            if not isinstance(sessions, list):
                return jsonify({"ok": False, "error": "data must be a list"}), 400

            db_path = session_manager.PATH_DB
            imported_sessions = 0
            imported_messages = 0

            with sqlite3.connect(db_path) as conn:
                if mode == "replace":
                    conn.execute("DELETE FROM messages")
                    conn.execute("DELETE FROM sessions")

                for s in sessions:
                    try:
                        new_sid = str(_uuid.uuid4())
                        now = _dt.now().isoformat()
                        conn.execute(
                            """INSERT OR IGNORE INTO sessions
                               (id, title, created_at, updated_at, privacy_mode, is_incognito, archived)
                               VALUES (?,?,?,?,?,?,?)""",
                            (
                                new_sid,
                                s.get("title", "Imported Chat"),
                                s.get("created_at") or now,
                                s.get("updated_at") or now,
                                s.get("privacy_mode", "normal"),
                                int(s.get("is_incognito", 0)),
                                int(s.get("archived", 0)),
                            )
                        )
                        imported_sessions += 1

                        for msg in s.get("messages", []):
                            try:
                                conn.execute(
                                    """INSERT INTO messages
                                       (session_id, timestamp, role, content)
                                       VALUES (?,?,?,?)""",
                                    (
                                        new_sid,
                                        msg.get("timestamp") or now,
                                        msg.get("role", "user"),
                                        msg.get("content") or msg.get("message", ""),
                                    )
                                )
                                imported_messages += 1
                            except Exception as msg_e:
                                logger.error(f"[BACKUP] history msg error: {msg_e}")
                    except Exception as se:
                        logger.error(f"[BACKUP] history session error: {se}")

            return jsonify({
                "ok": True,
                "imported_sessions": imported_sessions,
                "imported_messages": imported_messages
            })
        except Exception as e:
            logger.error(f"[BACKUP] history_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════
    # EPISODIC MEMORY (per-user history.db)
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/hecos/api/memory/backup", methods=["GET"], endpoint="mbkp_memory_backup")
    def memory_backup():
        """Esporta la memoria episodica (tutti gli utenti) come JSON."""
        try:
            from hecos.memory import brain_interface
            import sqlite3, os

            users_dir = brain_interface._USERS_DIR
            all_data = {}

            if os.path.isdir(users_dir):
                for uid in os.listdir(users_dir):
                    db_path = brain_interface._db_path(uid)
                    if not os.path.exists(db_path):
                        continue
                    with sqlite3.connect(db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        rows = conn.execute(
                            "SELECT * FROM history ORDER BY id ASC"
                        ).fetchall()
                    all_data[uid] = [dict(r) for r in rows]

            total = sum(len(v) for v in all_data.values())
            return jsonify({"ok": True, "count": total, "data": all_data})
        except Exception as e:
            logger.error(f"[BACKUP] memory_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/memory/restore", methods=["POST"], endpoint="mbkp_memory_restore")
    def memory_restore():
        """
        Ripristina la memoria episodica da JSON.
        Body: { data: { user_id: [...rows...] }, mode: "duplicate"|"replace" }
        """
        try:
            from hecos.memory import brain_interface
            import sqlite3
            from datetime import datetime as _dt

            body = request.get_json(force=True) or {}
            data = body.get("data", {})
            mode = body.get("mode", "duplicate")

            if not isinstance(data, dict):
                return jsonify({"ok": False, "error": "data must be a dict {user_id: [rows]}"}), 400

            imported = 0
            for uid, rows in data.items():
                try:
                    brain_interface.initialize_user_vault(uid)
                    db_path = brain_interface._db_path(uid)
                    with sqlite3.connect(db_path) as conn:
                        if mode == "replace":
                            conn.execute("DELETE FROM history")
                        for r in rows:
                            try:
                                conn.execute(
                                    """INSERT INTO history
                                       (timestamp, role, message, session_id, persona_name)
                                       VALUES (?,?,?,?,?)""",
                                    (
                                        r.get("timestamp") or _dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        r.get("role", "user"),
                                        r.get("message", ""),
                                        r.get("session_id"),
                                        r.get("persona_name"),
                                    )
                                )
                                imported += 1
                            except Exception as row_e:
                                logger.error(f"[BACKUP] memory row error: {row_e}")
                except Exception as uid_e:
                    logger.error(f"[BACKUP] memory user '{uid}' error: {uid_e}")

            return jsonify({"ok": True, "imported": imported})
        except Exception as e:
            logger.error(f"[BACKUP] memory_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════
    # FLOWS
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/hecos/api/backup_module/flows/backup", methods=["GET"], endpoint="mbkp_flows_backup_unique")
    def flows_backup():
        """Esporta tutti i flow come JSON (dict {flow_id: flow_data})."""
        try:
            from hecos.modules.flows.storage import list_flows, get_flow
            summaries = list_flows()
            all_flows = {}
            for s in summaries:
                flow_id = s["id"]
                data = get_flow(flow_id)
                if data:
                    all_flows[flow_id] = data

            return jsonify({"ok": True, "count": len(all_flows), "data": all_flows})
        except Exception as e:
            logger.error(f"[BACKUP] flows_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/backup_module/flows/restore", methods=["POST"], endpoint="mbkp_flows_restore_unique")
    def flows_restore():
        """
        Ripristina flow da JSON.
        Body: { data: { flow_id: {...} }, mode: "duplicate"|"replace" }
        """
        try:
            from hecos.modules.flows.storage import save_flow, _get_flows_dir, delete_flow, list_flows
            import os

            body = request.get_json(force=True) or {}
            flows = body.get("data", {})
            mode = body.get("mode", "duplicate")

            if not isinstance(flows, dict):
                return jsonify({"ok": False, "error": "data must be a dict {flow_id: flow_data}"}), 400

            if mode == "replace":
                for existing in list_flows():
                    delete_flow(existing["id"])

            imported = 0
            for flow_id, flow_data in flows.items():
                try:
                    if isinstance(flow_data, dict):
                        # Preserve original id
                        flow_data["id"] = flow_id
                        save_flow(flow_data)
                        imported += 1
                except Exception as fe:
                    logger.error(f"[BACKUP] flows flow '{flow_id}' error: {fe}")

            return jsonify({"ok": True, "imported": imported})
        except Exception as e:
            logger.error(f"[BACKUP] flows_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════
    # USERS
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/hecos/api/backup_module/users/backup", methods=["GET"], endpoint="mbkp_users_backup_unique")
    def users_backup():
        """Esporta tutti gli utenti (senza password hash) come JSON."""
        try:
            from hecos.core.auth.auth_manager import auth_mgr
            import sqlite3

            # Get all users via auth_mgr
            try:
                all_users = auth_mgr.list_users()
            except Exception:
                # Fallback: direct DB read
                db_path = getattr(auth_mgr, "_db_path", None) or getattr(auth_mgr, "db_path", None)
                if db_path and __import__("os").path.exists(db_path):
                    with sqlite3.connect(db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        rows = conn.execute("SELECT * FROM users").fetchall()
                        all_users = [dict(r) for r in rows]
                else:
                    all_users = []

            # Strip password hashes for security
            safe_users = []
            for u in all_users:
                su = dict(u)
                su.pop("password_hash", None)
                su.pop("password", None)
                safe_users.append(su)

            return jsonify({"ok": True, "count": len(safe_users), "data": safe_users})
        except Exception as e:
            logger.error(f"[BACKUP] users_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/backup_module/users/restore", methods=["POST"], endpoint="mbkp_users_restore_unique")
    def users_restore():
        """
        Ripristina utenti da JSON (solo campi profilo, NON le password).
        Body: { data: [...], mode: "skip_existing"|"update" }
        """
        try:
            from hecos.core.auth.auth_manager import auth_mgr

            body = request.get_json(force=True) or {}
            users = body.get("data", [])
            mode = body.get("mode", "skip_existing")

            if not isinstance(users, list):
                return jsonify({"ok": False, "error": "data must be a list"}), 400

            imported = 0
            skipped = 0
            for u in users:
                username = u.get("username")
                if not username:
                    continue
                try:
                    existing = auth_mgr.get_user(username)
                    if existing and mode == "skip_existing":
                        skipped += 1
                        continue

                    profile_fields = {
                        k: v for k, v in u.items()
                        if k not in ("username", "password_hash", "password", "id")
                    }
                    if existing:
                        auth_mgr.update_profile(username, profile_fields)
                    else:
                        # Create user with a temporary password — admin must reset
                        try:
                            auth_mgr.create_user(
                                username=username,
                                password="Hecos_RestoreTemp_2025!",
                                role=u.get("role", "user")
                            )
                            auth_mgr.update_profile(username, profile_fields)
                        except Exception:
                            pass
                    imported += 1
                except Exception as ue:
                    logger.error(f"[BACKUP] users row error '{username}': {ue}")

            return jsonify({"ok": True, "imported": imported, "skipped": skipped})
        except Exception as e:
            logger.error(f"[BACKUP] users_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM CONFIG (config/data/*.yaml, *.json)
    # ═══════════════════════════════════════════════════════════════════════════

    @app.route("/hecos/api/system_config/backup", methods=["GET"], endpoint="mbkp_system_config_backup")
    def system_config_backup():
        """Esporta tutti i file YAML/JSON da config/data."""
        try:
            import os
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(root, "config", "data")
            
            all_files = {}
            if os.path.isdir(data_dir):
                logger.debug(f"[BACKUP] Scanning config directory: {data_dir}")
                for fname in os.listdir(data_dir):
                    if fname.endswith(".yaml") or fname.endswith(".json"):
                        # Skip backup config itself to avoid recursion/overwriting loops, 
                        # or keep it? It's fine to keep it, but during restore we might overwrite it.
                        if fname == "backup_config.json":
                            continue
                        fpath = os.path.join(data_dir, fname)
                        if os.path.isfile(fpath):
                            with open(fpath, "r", encoding="utf-8") as f:
                                all_files[fname] = f.read()
                logger.debug(f"[BACKUP] Collected {len(all_files)} files from {data_dir}")
            else:
                logger.warning(f"[BACKUP] Config directory not found: {data_dir}")

            return jsonify({
                "ok": True, 
                "_is_files_bundle": True,
                "files": {
                    f"config_data/{fname}": content for fname, content in all_files.items()
                }
            })
        except Exception as e:
            logger.error(f"[BACKUP] system_config_backup error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.route("/hecos/api/system_config/restore", methods=["POST"], endpoint="mbkp_system_config_restore")
    def system_config_restore():
        """
        Ripristina file di configurazione in config/data.
        Body: { data: { "filename.yaml": "content..." }, mode: "replace"|"duplicate" }
        Note: "duplicate" currently just overwrites for files, since config must be exact.
        """
        try:
            import os
            body = request.get_json(force=True) or {}
            files_data = body.get("data", {})
            
            if not isinstance(files_data, dict):
                return jsonify({"ok": False, "error": "data must be a dict {filename: content}"}), 400

            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(root, "config", "data")
            os.makedirs(data_dir, exist_ok=True)
            logger.debug(f"[BACKUP] Restoring configs to: {data_dir}")
            
            imported = 0
            for fname, content in files_data.items():
                if not (fname.endswith(".yaml") or fname.endswith(".json")):
                    continue
                # Simple security check to prevent path traversal
                if "/" in fname or "\\" in fname or ".." in fname:
                    continue
                    
                fpath = os.path.join(data_dir, fname)
                try:
                    # Create a backup of the existing file just in case
                    if os.path.exists(fpath):
                        import shutil
                        shutil.copy(fpath, fpath + ".bak")
                        
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)
                    imported += 1
                except Exception as fe:
                    logger.error(f"[BACKUP] system_config write error '{fname}': {fe}")

            return jsonify({"ok": True, "imported": imported})
        except Exception as e:
            logger.error(f"[BACKUP] system_config_restore error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    logger.info("BACKUP", "✅ Module backup routes registered (calendar, reminders, history, memory, flows, users, system_config).")
