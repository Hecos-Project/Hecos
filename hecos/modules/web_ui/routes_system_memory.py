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

    # ── GET /api/memory/backup — full chat+RAG backup ─────────────────────────
    @app.route("/api/memory/backup", methods=["GET"])
    def memory_full_backup():
        """
        Returns a combined JSON snapshot of all chat sessions (with messages)
        plus the RAG source registry (sources.json metadata).
        The actual LanceDB vector data is NOT exported (it's binary/large);
        only the human-readable source registry is included.
        """
        from datetime import datetime, timezone
        try:
            # --- Chat history ---
            from hecos.memory import session_manager as sm
            active   = sm.get_sessions(include_archived=False)
            archived = sm.get_sessions(include_archived=True)
            all_sessions = {s["id"]: s for s in active + archived}.values()
            sessions_data = []
            for s in all_sessions:
                msgs = sm.get_session_messages(s["id"])
                sessions_data.append({**s, "messages": msgs})

            # --- RAG source registry ---
            from hecos.core.rag.store import get_all_sources
            rag_sources = get_all_sources()

            return jsonify({
                "ok": True,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "chat": {
                    "session_count": len(sessions_data),
                    "sessions": sessions_data
                },
                "rag": {
                    "source_count": len(rag_sources),
                    "sources": rag_sources
                }
            })
        except Exception as exc:
            logger.error(f"[WebUI] memory_full_backup error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

    # ── POST /api/memory/restore — restore from full backup ───────────────────
    @app.route("/api/memory/restore", methods=["POST"])
    def memory_full_restore():
        """
        Restores chat sessions from a combined memory backup JSON.
        The RAG vector store cannot be re-created from this backup (sources metadata
        only); the user needs to re-ingest documents for full vector recovery.
        Body: { chat: { sessions: [...] }, mode: "duplicate" | "replace" }
        """
        import sqlite3, uuid as _uuid
        from datetime import datetime
        from hecos.memory.session_manager import PATH_DB, _is_ram_mode

        try:
            data = request.get_json(force=True) or {}
            mode = data.get("mode", "duplicate")
            chat_data = data.get("chat", {})
            sessions_payload = chat_data.get("sessions", [])

            from hecos.memory import session_manager as sm

            if mode == "replace":
                sm.delete_all_sessions()

            restored_sessions = 0
            restored_messages = 0

            for s in sessions_payload:
                if _is_ram_mode(s.get("privacy_mode", "normal")):
                    continue

                new_sid = str(_uuid.uuid4())
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                conn = sqlite3.connect(PATH_DB)
                cur  = conn.cursor()
                cur.execute(
                    "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at, privacy_mode, is_incognito, is_archived) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        new_sid,
                        s.get("title", "Restored Session"),
                        s.get("created_at", now),
                        s.get("updated_at", now),
                        "normal",
                        0,
                        int(s.get("is_archived", 0))
                    )
                )
                conn.commit()
                conn.close()
                restored_sessions += 1

                try:
                    try:
                        from flask_login import current_user
                        uid = current_user.username if current_user and current_user.is_authenticated else "admin"
                    except Exception:
                        uid = "admin"

                    from hecos.memory.brain_interface import _db_path
                    import os
                    db_path = _db_path(uid)
                    if not os.path.exists(db_path):
                        continue

                    with sqlite3.connect(db_path) as vconn:
                        vcur = vconn.cursor()
                        for msg in s.get("messages", []):
                            vcur.execute(
                                "INSERT INTO history (timestamp, role, message, session_id) VALUES (?, ?, ?, ?)",
                                (msg.get("timestamp", now), msg.get("role", "user"), msg.get("message", ""), new_sid)
                            )
                        vconn.commit()
                        restored_messages += len(s.get("messages", []))
                except Exception as msg_err:
                    logger.error(f"[WebUI] restore messages error for {new_sid}: {msg_err}")

            return jsonify({
                "ok": True,
                "restored_sessions": restored_sessions,
                "restored_messages": restored_messages,
                "note": "RAG vector data cannot be auto-restored. Please re-ingest your documents."
            }), 201
        except Exception as exc:
            logger.error(f"[WebUI] memory_full_restore error: {exc}")
            return jsonify({"ok": False, "error": str(exc)}), 500

