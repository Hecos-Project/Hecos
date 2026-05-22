"""
MODULE: RAG Vector Store — LanceDB Adapter
DESCRIPTION: Wraps LanceDB for vector storage & similarity search.
             Multi-collection: one per (user_id, namespace) pair.
             Falls back silently if lancedb is not installed.
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from hecos.core.logging import logger


# ── Paths ──────────────────────────────────────────────────────────────────────

_HERE = os.path.dirname(__file__)
_HECOS_DIR = os.path.normpath(os.path.join(_HERE, "..", ".."))
_DEFAULT_PERSIST = os.path.join(_HECOS_DIR, "memory", "vector_store")
_SOURCES_FILE = os.path.join(_DEFAULT_PERSIST, "sources.json")


# ── LanceDB availability check ─────────────────────────────────────────────────

def _lancedb_available() -> bool:
    try:
        import lancedb  # noqa: F401
        return True
    except ImportError:
        return False

# Execute on main thread at import time. Prevents major Flask/Rust deadlocks
# that occur if Pyarrow/Lance C++ tries to boot inside a worker thread.
LANCEDB_IS_AVAILABLE = _lancedb_available()


# ── Source tracker (lightweight JSON registry) ─────────────────────────────────

def _load_sources() -> dict:
    if os.path.exists(_SOURCES_FILE):
        try:
            with open(_SOURCES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_sources(data: dict):
    os.makedirs(os.path.dirname(_SOURCES_FILE), exist_ok=True)
    with open(_SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_source(source: str, meta: dict = None):
    """Track an ingested source in sources.json."""
    sources = _load_sources()
    sources[source] = {
        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **(meta or {})
    }
    _save_sources(sources)


def get_all_sources() -> dict:
    return _load_sources()


def remove_source(source: str):
    sources = _load_sources()
    sources.pop(source, None)
    _save_sources(sources)


# ── LanceDB Store ──────────────────────────────────────────────────────────────

class LanceDBStore:
    """
    Manages a LanceDB database with multiple tables (collections).
    Table naming: f"{user_id}__{namespace}"  e.g. "admin__episodic"
    """

    NAMESPACES = ("episodic", "knowledge", "documents")

    def __init__(self, persist_path: str = _DEFAULT_PERSIST, dimension: int = 384):
        if not LANCEDB_IS_AVAILABLE:
            raise RuntimeError("[RAG][Store] lancedb is not installed.")
        import lancedb
        self._persist_path = persist_path
        self._dimension = dimension
        os.makedirs(persist_path, exist_ok=True)
        self._db = lancedb.connect(persist_path)
        logger.info(f"[RAG][Store] LanceDB connected at: {persist_path}")

    def _table_name(self, user_id: str, namespace: str) -> str:
        safe_uid = user_id.replace("-", "_")
        return f"{safe_uid}__{namespace}"

    def _get_or_create_table(self, user_id: str, namespace: str):
        """Open existing table or create with schema."""
        import pyarrow as pa
        tname = self._table_name(user_id, namespace)
        if tname in self._db.table_names():
            return self._db.open_table(tname)
        schema = pa.schema([
            pa.field("id",          pa.string()),
            pa.field("text",        pa.string()),
            pa.field("vector",      pa.list_(pa.float32(), self._dimension)),
            pa.field("source",      pa.string()),
            pa.field("session_id",  pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("timestamp",   pa.string()),
            pa.field("meta",        pa.string()),
        ])
        return self._db.create_table(tname, schema=schema)

    def upsert(self, user_id: str, namespace: str, records: List[Dict[str, Any]]):
        """
        Insert or update records. Each record must have:
        id, text, vector, source, session_id, chunk_index, timestamp, meta
        """
        if not records:
            return
        import pyarrow as pa
        table = self._get_or_create_table(user_id, namespace)
        # Delete existing entries with same IDs to simulate upsert
        ids = [r["id"] for r in records]
        try:
            table.delete(f"id IN ({', '.join(repr(i) for i in ids)})")
        except Exception:
            pass
        table.add(records)
        logger.debug(f"[RAG][Store] Upserted {len(records)} records → {self._table_name(user_id, namespace)}")

    def search(self, user_id: str, namespace: str,
               query_vector: List[float],
               top_k: int = 5,
               source_filter: Optional[str] = None) -> List[Dict]:
        """
        Perform approximate nearest-neighbour search.
        Returns list of dicts with text, source, _distance, etc.
        """
        tname = self._table_name(user_id, namespace)
        if tname not in self._db.table_names():
            return []
        table = self._db.open_table(tname)
        q = table.search(query_vector).limit(top_k)
        if source_filter:
            q = q.where(f"source = '{source_filter}'", prefilter=True)
        try:
            results = q.to_list()
            return results
        except Exception as e:
            logger.error(f"[RAG][Store] search error: {e}")
            return []

    def delete_by_source(self, user_id: str, namespace: str, source: str) -> bool:
        """Remove all chunks from a given source."""
        tname = self._table_name(user_id, namespace)
        if tname not in self._db.table_names():
            return True
        try:
            table = self._db.open_table(tname)
            table.delete(f"source = '{source}'")
            remove_source(source)
            return True
        except Exception as e:
            logger.error(f"[RAG][Store] delete_by_source error: {e}")
            return False

    def delete_by_session(self, user_id: str, namespace: str, session_id: str) -> bool:
        tname = self._table_name(user_id, namespace)
        if tname not in self._db.table_names():
            return True
        try:
            table = self._db.open_table(tname)
            table.delete(f"session_id = '{session_id}'")
            return True
        except Exception as e:
            logger.error(f"[RAG][Store] delete_by_session error: {e}")
            return False

    def wipe(self, user_id: str = None, namespace: str = None):
        """
        Wipe tables. If user_id is None, wipe ALL tables (full reset).
        If only user_id given, wipe all namespaces for that user.
        If both given, wipe just that table.
        """
        all_tables = self._db.table_names()
        for tname in all_tables:
            uid, ns = (tname.split("__", 1) + [""])[:2]
            if user_id and uid != user_id.replace("-", "_"):
                continue
            if namespace and ns != namespace:
                continue
            try:
                self._db.drop_table(tname)
                logger.info(f"[RAG][Store] Wiped table: {tname}")
            except Exception as e:
                logger.warning(f"[RAG][Store] Could not wipe {tname}: {e}")
        _save_sources({})

    def count(self, user_id: str = None) -> int:
        """Total document chunk count across all tables for a user."""
        total = 0
        for tname in self._db.table_names():
            if user_id and not tname.startswith(user_id.replace("-", "_")):
                continue
            try:
                total += self._db.open_table(tname).count_rows()
            except Exception:
                pass
        return total


# ── Stub store (no-op) ─────────────────────────────────────────────────────────

class StubStore:
    """Used when lancedb is not installed. All operations are no-ops."""
    def upsert(self, *a, **kw): pass
    def search(self, *a, **kw) -> list: return []
    def delete_by_source(self, *a, **kw) -> bool: return True
    def delete_by_session(self, *a, **kw) -> bool: return True
    def wipe(self, *a, **kw): pass
    def count(self, *a, **kw) -> int: return 0


# ── Factory ────────────────────────────────────────────────────────────────────

def get_store(persist_path: str = _DEFAULT_PERSIST, dimension: int = 384):
    if LANCEDB_IS_AVAILABLE:
        try:
            return LanceDBStore(persist_path, dimension)
        except Exception as e:
            logger.error(f"[RAG][Store] LanceDB init failed: {e}")
    logger.warning("[RAG][Store] Using StubStore (lancedb unavailable).")
    return StubStore()
