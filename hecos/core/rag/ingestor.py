"""
MODULE: RAG Ingestor
DESCRIPTION: Multi-format document ingestion pipeline.
             Supported: TXT, MD, PDF (via pypdf), URL (via requests+html2text).
             Tracks all ingested sources in sources.json.
"""

from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import List, Callable, Optional
from hecos.core.logging import logger


# ── Format readers ─────────────────────────────────────────────────────────────

def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_pdf(path: str) -> str:
    try:
        import pypdf  # noqa
        reader = pypdf.PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("[RAG][Ingestor] pypdf not installed — PDF read skipped.")
        return ""
    except Exception as e:
        logger.error(f"[RAG][Ingestor] PDF read error for {path}: {e}")
        return ""


def _read_url(url: str) -> str:
    try:
        import requests
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "HecosRAG/1.0"})
        resp.raise_for_status()
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            return h.handle(resp.text)
        except ImportError:
            # Fallback: strip HTML tags naively
            import re
            return re.sub(r'<[^>]+>', ' ', resp.text)
    except Exception as e:
        logger.error(f"[RAG][Ingestor] URL read error for {url}: {e}")
        return ""


def _dispatch_reader(source: str) -> str:
    """Select the appropriate reader based on source type."""
    lo = source.lower()
    if lo.startswith(("http://", "https://")):
        return _read_url(source)
    ext = os.path.splitext(lo)[1]
    if ext == ".pdf":
        return _read_pdf(source)
    # Default: plain text / markdown
    return _read_txt(source)


# ── Ingestion record ───────────────────────────────────────────────────────────

class IngestionResult:
    def __init__(self, source: str, chunk_count: int = 0, error: str = ""):
        self.source = source
        self.chunk_count = chunk_count
        self.error = error

    @property
    def ok(self) -> bool:
        return not self.error


# ── Ingestor ───────────────────────────────────────────────────────────────────

class Ingestor:
    """
    Ingests text/files/URLs into the vector store.
    Caller provides the chunker, embedder, and store.
    """

    def __init__(self, chunker, embedder, store,
                 namespace: str = "knowledge",
                 progress_cb: Optional[Callable[[str], None]] = None):
        """
        Args:
            chunker:     TextChunker instance
            embedder:    Embedder instance
            store:       LanceDB store instance
            namespace:   LanceDB collection namespace ('knowledge', 'documents', 'episodic')
            progress_cb: Optional callback for UI progress reporting
        """
        self._chunker = chunker
        self._embedder = embedder
        self._store = store
        self._namespace = namespace
        self._progress = progress_cb or (lambda msg: None)

    # ── Public API ─────────────────────────────────────────────────────────────

    def ingest_text(self, text: str, source: str = "manual",
                    user_id: str = "admin",
                    session_id: str = "",
                    namespace: str = None) -> IngestionResult:
        """Ingest a text string directly."""
        ns = namespace or self._namespace
        if not text or not text.strip():
            return IngestionResult(source, error="Empty text.")
        try:
            self._progress(f"Chunking '{source}'...")
            chunks = self._chunker.split(text, source=source)
            if not chunks:
                return IngestionResult(source, error="No chunks produced.")

            self._progress(f"Embedding {len(chunks)} chunks...")
            vectors = self._embedder.embed_texts([c.text for c in chunks])

            records = []
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for chunk, vec in zip(chunks, vectors):
                records.append({
                    "id":          str(uuid.uuid4()),
                    "text":        chunk.text,
                    "vector":      vec,
                    "source":      source,
                    "session_id":  session_id,
                    "chunk_index": chunk.index,
                    "timestamp":   now,
                    "meta":        "",
                })

            self._store.upsert(user_id, ns, records)

            # Track in sources registry
            from hecos.core.rag.store import register_source
            register_source(source, {"chunks": len(records), "user_id": user_id, "namespace": ns})

            self._progress(f"Ingested '{source}': {len(records)} chunks.")
            logger.info(f"[RAG][Ingestor] '{source}' → {len(records)} chunks in [{ns}] for user '{user_id}'")
            return IngestionResult(source, chunk_count=len(records))

        except Exception as e:
            msg = f"Ingestion error for '{source}': {e}"
            logger.error(f"[RAG][Ingestor] {msg}")
            return IngestionResult(source, error=str(e))

    def ingest_file(self, path: str, user_id: str = "admin",
                    namespace: str = None) -> IngestionResult:
        """Read file → ingest. Supports .txt, .md, .pdf."""
        if not os.path.exists(path):
            return IngestionResult(path, error="File not found.")
        self._progress(f"Reading file: {os.path.basename(path)}")
        text = _dispatch_reader(path)
        if not text.strip():
            return IngestionResult(path, error="File returned empty text.")
        source_name = os.path.basename(path)
        return self.ingest_text(text, source=source_name, user_id=user_id,
                                namespace=namespace)

    def ingest_url(self, url: str, user_id: str = "admin",
                   namespace: str = None) -> IngestionResult:
        """Fetch URL → ingest its text content."""
        self._progress(f"Fetching URL: {url[:60]}...")
        text = _read_url(url)
        if not text.strip():
            return IngestionResult(url, error="URL returned empty content.")
        return self.ingest_text(text, source=url, user_id=user_id,
                                namespace=namespace)

    def ingest_message(self, role: str, message: str,
                       user_id: str = "admin",
                       session_id: str = "") -> IngestionResult:
        """
        Auto-ingest a single chat exchange from episodic memory into the
        'episodic' namespace. Called by brain_interface when auto_ingest is ON.
        """
        label = f"session:{session_id}:{role}"
        return self.ingest_text(message, source=label, user_id=user_id,
                                session_id=session_id, namespace="episodic")

    def delete_source(self, source: str, user_id: str = "admin",
                      namespace: str = None) -> bool:
        ns = namespace or self._namespace
        return self._store.delete_by_source(user_id, ns, source)
