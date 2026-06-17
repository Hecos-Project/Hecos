"""
routes_rag.py
────────────────────────────────────────────────────────────────────────────
Hecos WebUI — RAG Vector Memory APIs
Registers:
  GET  /api/rag/status
  POST /api/rag/ingest
  POST /api/rag/search
  POST /api/rag/wipe
  GET  /api/rag/sources
  POST /api/rag/delete_source
────────────────────────────────────────────────────────────────────────────
"""
from flask import jsonify, request


def init_rag_routes(app, cfg_mgr, logger):

    def _engine():
        from hecos.core.rag import get_rag_engine
        return get_rag_engine(cfg_mgr.config)

    # ── Status ─────────────────────────────────────────────────────────────────
    @app.route("/api/rag/status", methods=["GET"])
    def rag_status():
        """Returns engine status, total chunk count, embedder model, and sources."""
        try:
            engine = _engine()
            user_id = request.args.get("user_id", "admin")
            stats = engine.stats(user_id=user_id)
            return jsonify({"ok": True, **stats})
        except Exception as e:
            logger.error(f"[RAG] status error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Ingest text / file / URL ───────────────────────────────────────────────
    @app.route("/api/rag/ingest", methods=["POST"])
    def rag_ingest():
        """
        Body (JSON):
          type: 'text' | 'file' | 'url'
          content: <text> | <absolute path> | <url>
          source: optional label
          namespace: 'knowledge' | 'documents' | 'episodic'  (default: knowledge)
          user_id: optional (default: admin)
        """
        try:
            data = request.get_json(force=True) or {}
            ingest_type = data.get("type", "text")
            content     = data.get("content", "").strip()
            source      = data.get("source", "webui_upload")
            namespace   = data.get("namespace", "knowledge")
            user_id     = data.get("user_id", "admin")

            if not content:
                return jsonify({"ok": False, "error": "Empty content"}), 400

            engine = _engine()
            if not engine.is_enabled():
                return jsonify({"ok": False, "error": "RAG is disabled in configuration."}), 400

            if ingest_type == "file":
                result = engine.ingest_file(content, user_id=user_id, namespace=namespace)
            elif ingest_type == "url":
                result = engine.ingest_url(content, user_id=user_id, namespace=namespace)
            else:
                result = engine.ingest_text(content, source=source,
                                            user_id=user_id, namespace=namespace)

            if result and result.ok:
                return jsonify({"ok": True, "chunks": result.chunk_count, "source": result.source})
            err = result.error if result else "Unknown error"
            return jsonify({"ok": False, "error": err}), 500

        except Exception as e:
            logger.error(f"[RAG] ingest error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Search (debug / manual) ────────────────────────────────────────────────
    @app.route("/api/rag/search", methods=["POST"])
    def rag_search():
        """Manual semantic search for debug/exploration via the UI."""
        try:
            data     = request.get_json(force=True) or {}
            query    = data.get("query", "")
            user_id  = data.get("user_id", "admin")
            top_k    = int(data.get("top_k", 5))
            namespaces = data.get("namespaces")

            if not query:
                return jsonify({"ok": False, "error": "No query provided"}), 400

            engine = _engine()
            chunks = engine.search(query, user_id=user_id,
                                   namespaces=namespaces, top_k=top_k)
            results = [
                {"text": c.text[:500], "source": c.source,
                 "score": round(c.score, 4), "session_id": c.session_id}
                for c in chunks
            ]
            return jsonify({"ok": True, "results": results, "count": len(results)})

        except Exception as e:
            logger.error(f"[RAG] search error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Wipe vector store ──────────────────────────────────────────────────────
    @app.route("/api/rag/wipe", methods=["POST"])
    def rag_wipe():
        """Wipes all vector data for the given user (or all users if admin wipe)."""
        try:
            data    = request.get_json(force=True) or {}
            user_id = data.get("user_id", "admin")
            scope   = data.get("scope", "user")  # 'user' | 'all'

            engine = _engine()
            engine.wipe(user_id=None if scope == "all" else user_id)
            msg = f"Vector store wiped (scope={scope})."
            logger.info(f"[RAG] {msg}")
            return jsonify({"ok": True, "message": msg})

        except Exception as e:
            logger.error(f"[RAG] wipe error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Sources registry ───────────────────────────────────────────────────────
    @app.route("/api/rag/sources", methods=["GET"])
    def rag_sources():
        """Returns the list of all ingested sources from sources.json."""
        try:
            from hecos.core.rag.store import get_all_sources
            sources = get_all_sources()
            return jsonify({"ok": True, "sources": sources})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Source chunks ──────────────────────────────────────────────────────────
    @app.route("/api/rag/source_chunks", methods=["GET"])
    def rag_source_chunks():
        """Retrieve all text chunks for a specific source."""
        try:
            source = request.args.get("source", "")
            namespace = request.args.get("namespace", "knowledge")
            user_id = request.args.get("user_id", "admin")
            if not source:
                return jsonify({"ok": False, "error": "No source"}), 400

            engine = _engine()
            if not engine._ensure_init():
                return jsonify({"ok": False, "error": "RAG disabled"}), 400

            chunks = engine._store.get_chunks_by_source(user_id, namespace, source)
            texts = [c.get("text", "") for c in chunks]
            return jsonify({"ok": True, "chunks": texts})
        except Exception as e:
            logger.error(f"[RAG] source_chunks error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500

    # ── Delete specific source ─────────────────────────────────────────────────
    @app.route("/api/rag/delete_source", methods=["POST"])
    def rag_delete_source():
        """Remove a specific source from the vector store."""
        try:
            data      = request.get_json(force=True) or {}
            source    = data.get("source", "")
            namespace = data.get("namespace", "knowledge")
            user_id   = data.get("user_id", "admin")

            if not source:
                return jsonify({"ok": False, "error": "No source specified"}), 400

            engine = _engine()
            ok = engine.delete_source(source, user_id=user_id, namespace=namespace)
            return jsonify({"ok": ok})

        except Exception as e:
            logger.error(f"[RAG] delete_source error: {e}")
            return jsonify({"ok": False, "error": str(e)}), 500
