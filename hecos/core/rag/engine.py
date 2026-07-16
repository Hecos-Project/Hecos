"""
MODULE: RAG Engine
DESCRIPTION: Central orchestrator for the Hecos RAG system.
             Provides a single high-level interface: ingest_* + search + context_for_query.
             Reads config from `cognition.rag` in system.yaml.
             All sub-systems are lazy-initialized on first use.
"""

from __future__ import annotations
import os
import threading
from typing import List, Optional, Callable
from hecos.core.logging import logger


# ── Paths ──────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_HECOS_DIR = os.path.normpath(os.path.join(_HERE, "..", ".."))
_DEFAULT_PERSIST = os.path.join(_HECOS_DIR, "memory", "vector_store")


# ── Engine status constants ────────────────────────────────────────────────────
STATUS_ONLINE   = "ONLINE"
STATUS_STANDBY  = "STANDBY"   # not enabled in config
STATUS_DEGRADED = "DEGRADED"  # enabled but deps missing
STATUS_INDEXING = "INDEXING"


class RAGEngine:
    """
    Hecos RAG Engine — central singleton.
    Lazy-initializes sub-systems on first use.
    """

    def __init__(self, config: dict = None):
        self._config = config or {}
        self._rag_cfg: dict = {}
        self._status = STATUS_STANDBY
        self._embedder = None
        self._store    = None
        self._chunker  = None
        self._retriever = None
        self._ingestor  = None
        self._initialized = False
        self._init_lock = threading.Lock()  # Prevents concurrent initialization

    # ── Config ─────────────────────────────────────────────────────────────────

    def reload_config(self, config: dict):
        """Hot-reload config. If key settings changed, reset so _ensure_init will re-run."""
        self._config = config
        new_rag_cfg = config.get("cognition", {}).get("rag", {})

        # Detect if we need to reinitialize
        old_enabled  = self._rag_cfg.get("enabled", False)
        old_embedder = self._rag_cfg.get("embedder", "")
        old_model    = self._rag_cfg.get("embedder_model", "")
        new_enabled  = new_rag_cfg.get("enabled", False)
        new_embedder = new_rag_cfg.get("embedder", "")
        new_model    = new_rag_cfg.get("embedder_model", "")

        self._rag_cfg = new_rag_cfg

        if (old_enabled != new_enabled or
                old_embedder != new_embedder or
                old_model != new_model):
            # Reset so next call triggers fresh initialization
            self._initialized = False
            self._status = STATUS_STANDBY if not new_enabled else self._status
            logger.info(
                f"[RAG][Engine] Config changed (enabled={new_enabled}, "
                f"embedder={new_embedder}/{new_model}) — will re-initialize."
            )

    def is_enabled(self) -> bool:
        if not self._rag_cfg:
            try:
                from hecos.app.config import ConfigManager
                cfg = ConfigManager().config
                self._rag_cfg = cfg.get("cognition", {}).get("rag", {})
            except Exception:
                self._rag_cfg = {}
        return self._rag_cfg.get("enabled", False)

    def status(self) -> str:
        return self._status

    # ── Lazy init ───────────────────────────────────────────────────────────────

    def _ensure_init(self) -> bool:
        """Initialize sub-systems. Returns True if fully operational."""
        # Fast path (no lock needed for the happy path)
        if self._initialized and self._status == STATUS_ONLINE:
            return True

        # Slow path: take lock so only one thread initializes at a time.
        # Other threads wait here and exit via the fast path above.
        with self._init_lock:
            # Re-check after acquiring lock (another thread may have finished)
            if self._initialized and self._status == STATUS_ONLINE:
                return True

            if not self._rag_cfg:
                try:
                    from hecos.app.config import ConfigManager
                    cfg = ConfigManager().config
                except Exception:
                    cfg = {}
                self._rag_cfg = cfg.get("cognition", {}).get("rag", {})

            if not self.is_enabled():
                self._status = STATUS_STANDBY
                return False

            try:
                from hecos.core.rag.embedder import get_embedder
                from hecos.core.rag.store    import get_store
                from hecos.core.rag.chunker  import get_chunker
                from hecos.core.rag.retriever import HybridRetriever
                from hecos.core.rag.ingestor  import Ingestor

                model_name    = self._rag_cfg.get("embedder_model", "BAAI/bge-small-en-v1.5")
                embedder_type = self._rag_cfg.get("embedder", "fastembed")
                chunk_size   = int(self._rag_cfg.get("chunk_size", 512))
                chunk_overlap= int(self._rag_cfg.get("chunk_overlap", 64))
                top_k        = int(self._rag_cfg.get("top_k", 5))
                threshold    = float(self._rag_cfg.get("similarity_threshold", 0.3))
                persist_path = self._rag_cfg.get("persist_path", "memory/vector_store")
                if not os.path.isabs(persist_path):
                    persist_path = os.path.join(_HECOS_DIR, persist_path)

                self._embedder  = get_embedder(embedder_type, model_name)
                self._store     = get_store(persist_path, self._embedder.dimension)
                self._chunker   = get_chunker("recursive", chunk_size, chunk_overlap)
                self._retriever = HybridRetriever(
                    store=self._store,
                    embedder=self._embedder,
                    top_k=top_k,
                    similarity_threshold=threshold,
                )
                self._ingestor = Ingestor(
                    chunker=self._chunker,
                    embedder=self._embedder,
                    store=self._store,
                    namespace="knowledge",
                )

                self._initialized = True
                self._status = STATUS_ONLINE
                logger.info(f"[RAG][Engine] Initialized — model={model_name}, top_k={top_k}, threshold={threshold}")
                return True

            except Exception as e:
                self._status = STATUS_DEGRADED
                logger.error(f"[RAG][Engine] Initialization failed: {e}")
                return False


    # ── Ingest API ──────────────────────────────────────────────────────────────

    def ingest_text(self, text: str, source: str = "manual",
                    user_id: str = "admin",
                    session_id: str = "",
                    namespace: str = "knowledge",
                    progress_cb: Callable[[str], None] = None):
        if not self._ensure_init():
            return None
        if progress_cb:
            self._ingestor._progress = progress_cb
        return self._ingestor.ingest_text(text, source=source, user_id=user_id,
                                          session_id=session_id, namespace=namespace)

    def ingest_file(self, path: str, user_id: str = "admin",
                    namespace: str = "documents",
                    progress_cb: Callable[[str], None] = None):
        if not self._ensure_init():
            return None
        if progress_cb:
            self._ingestor._progress = progress_cb
        # Use documents namespace for files by default
        orig_ns = self._ingestor._namespace
        self._ingestor._namespace = namespace
        result = self._ingestor.ingest_file(path, user_id=user_id)
        self._ingestor._namespace = orig_ns
        return result

    def ingest_url(self, url: str, user_id: str = "admin",
                   namespace: str = "knowledge",
                   progress_cb: Callable[[str], None] = None):
        if not self._ensure_init():
            return None
        if progress_cb:
            self._ingestor._progress = progress_cb
        return self._ingestor.ingest_url(url, user_id=user_id, namespace=namespace)

    def ingest_message(self, role: str, message: str,
                       user_id: str = "admin", session_id: str = ""):
        """Called by brain_interface when auto_ingest_history is True."""
        if not self._rag_cfg.get("auto_ingest_history", False):
            return
        if not self._ensure_init():
            return
        self._ingestor.ingest_message(role, message, user_id=user_id, session_id=session_id)

    # ── Search API ──────────────────────────────────────────────────────────────

    def search(self, query: str,
               user_id: str = "admin",
               namespaces: List[str] = None,
               top_k: int = None) -> List:
        """
        Perform semantic search across namespaces.
        Returns list of RetrievedChunk.
        """
        if not self._ensure_init():
            return []
        if namespaces is None:
            namespaces = ["knowledge", "documents", "episodic"]
        return self._retriever.retrieve_multi_namespace(
            query=query,
            user_id=user_id,
            namespaces=namespaces,
            top_k=top_k,
        )

    def context_for_query(self, query: str,
                          user_id: str = "admin",
                          namespaces: List[str] = None,
                          top_k: int = None,
                          max_chars: int = 3000) -> str:
        """
        High-level method: retrieve + format into a system-prompt block.
        Returns empty string if disabled or no results.
        """
        chunks = self.search(query, user_id=user_id, namespaces=namespaces, top_k=top_k)
        if not chunks:
            return ""
        from hecos.core.rag.retriever import format_context_block
        block = format_context_block(chunks, max_chars=max_chars)
        logger.debug(f"[RAG][Engine] context_for_query: {len(chunks)} chunks, {len(block)} chars")
        return block

    # ── Admin API ───────────────────────────────────────────────────────────────

    def wipe(self, user_id: str = None):
        if not self._ensure_init():
            return
        self._store.wipe(user_id=user_id)
        logger.info(f"[RAG][Engine] Vector store wiped for user={user_id or 'ALL'}")

    def delete_source(self, source: str, user_id: str = "admin",
                      namespace: str = "knowledge") -> bool:
        if not self._ensure_init():
            return False
        return self._store.delete_by_source(user_id, namespace, source)

    def stats(self, user_id: str = "admin") -> dict:
        from hecos.core.rag.store import get_all_sources

        # Attempt to initialize so the badge reflects true state
        if self.is_enabled() and not self._initialized:
            self._ensure_init()

        # Consistent reporting of sources and counts
        all_sources = get_all_sources()
        total_chunks = sum(s.get("chunks", 0) for s in all_sources.values())

        return {
            "status": self._status,
            "total_chunks": total_chunks,
            "sources": all_sources,
            "embedder": self._rag_cfg.get("embedder_model", "unknown"),
            "top_k": self._rag_cfg.get("top_k", 5),
            "threshold": self._rag_cfg.get("similarity_threshold", 0.3),
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine_instance: Optional[RAGEngine] = None


def get_rag_engine(config: dict = None) -> RAGEngine:
    """
    Returns the global singleton RAGEngine.
    Config is applied on first call or when explicitly provided.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RAGEngine(config or {})
    elif config is not None:
        _engine_instance.reload_config(config)
    return _engine_instance
