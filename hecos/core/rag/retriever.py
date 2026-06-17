"""
MODULE: RAG Retriever
DESCRIPTION: Hybrid dense + sparse retrieval with re-ranking.
             1. Dense: LanceDB cosine similarity search
             2. Sparse boost: BM25-style keyword scoring (pure Python)
             3. Re-ranker: weighted fusion of both scores
             4. Context formatter: builds the [KNOWLEDGE CONTEXT] system-prompt block
"""

from __future__ import annotations
import re
import math
from collections import Counter
from typing import List, Dict, Any
from hecos.core.logging import logger


# ── BM25-lite keyword scorer (no external deps) ────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return re.findall(r'\b[a-zA-Z\u00c0-\u024f]{2,}\b', text.lower())


def _bm25_score(query_tokens: List[str], doc_text: str,
                k1: float = 1.5, b: float = 0.75,
                avg_dl: float = 100.0) -> float:
    """Approximate BM25 score between query and a document string."""
    doc_tokens = _tokenize(doc_text)
    dl = len(doc_tokens)
    tf_map = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        tf = tf_map.get(qt, 0)
        if tf == 0:
            continue
        idf = math.log(1 + 1 / (tf + 0.5))  # simplified IDF (single-doc context)
        tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
        score += idf * tf_norm
    return score


# ── Result model ───────────────────────────────────────────────────────────────

class RetrievedChunk:
    __slots__ = ("text", "source", "score", "dense_score", "sparse_score",
                 "session_id", "meta")

    def __init__(self, text: str, source: str, dense_score: float = 0.0,
                 sparse_score: float = 0.0, session_id: str = "",
                 meta: str = ""):
        self.text = text
        self.source = source
        self.dense_score = dense_score
        self.sparse_score = sparse_score
        self.score = 0.0  # set after fusion
        self.session_id = session_id
        self.meta = meta


# ── Retriever ──────────────────────────────────────────────────────────────────

class HybridRetriever:
    """
    Hybrid retrieval: dense vector search + BM25 sparse re-ranking.
    Fuses scores as: score = α * dense + (1-α) * sparse
    """

    def __init__(self,
                 store,
                 embedder,
                 alpha: float = 0.7,
                 similarity_threshold: float = 0.3,
                 top_k: int = 5):
        """
        Args:
            store:                LanceDB store instance
            embedder:             Embedder instance
            alpha:                Weight for dense score (0–1). 1-alpha goes to sparse.
            similarity_threshold: Minimum fused score to include in results.
            top_k:                Max results to return.
        """
        self._store = store
        self._embedder = embedder
        self._alpha = alpha
        self._threshold = similarity_threshold
        self._top_k = top_k

    def retrieve(self,
                 query: str,
                 user_id: str = "admin",
                 namespace: str = "episodic",
                 top_k: int = None,
                 source_filter: str = None) -> List[RetrievedChunk]:
        """
        Main retrieval method. Returns ranked list of RetrievedChunk.
        """
        if not query or not query.strip():
            return []

        k = top_k or self._top_k
        # Retrieve more candidates from dense to give sparse re-ranker something to work with
        dense_candidates = k * 3

        logger.debug(f"[RAG][Retriever] Starting search for query='{query[:30]}...' top_k={k}")
        
        try:
            import time
            t0 = time.time()
            qvec = self._embedder.embed_text(query)
            logger.debug(f"[RAG][Retriever] Embedded query in {time.time()-t0:.3f}s")
        except Exception as e:
            logger.error(f"[RAG][Retriever] Embedding query failed: {e}")
            return []

        t1 = time.time()
        raw = self._store.search(
            user_id=user_id,
            namespace=namespace,
            query_vector=qvec,
            top_k=dense_candidates,
            source_filter=source_filter,
        )
        logger.debug(f"[RAG][Retriever] Dense search returned {len(raw)} results in {time.time()-t1:.3f}s")

        if not raw:
            return []

        # Normalize dense scores (LanceDB returns raw L2 or cosine distance)
        # Convert distance → similarity: sim = 1 / (1 + distance)
        query_tokens = _tokenize(query)
        chunks = []
        for r in raw:
            text = r.get("text", "")
            raw_dist = r.get("_distance", 0.0)
            dense_sim = 1.0 / (1.0 + raw_dist)  # higher = better
            sparse_sim = _bm25_score(query_tokens, text)
            chunks.append(RetrievedChunk(
                text=text,
                source=r.get("source", ""),
                dense_score=dense_sim,
                sparse_score=sparse_sim,
                session_id=r.get("session_id", ""),
                meta=r.get("meta", ""),
            ))

        # Normalise sparse scores to [0,1] range
        max_sparse = max((c.sparse_score for c in chunks), default=1.0)
        if max_sparse > 0:
            for c in chunks:
                c.sparse_score /= max_sparse

        # Fuse
        for c in chunks:
            c.score = self._alpha * c.dense_score + (1 - self._alpha) * c.sparse_score

        # Filter & sort
        filtered = [c for c in chunks if c.score >= self._threshold]
        filtered.sort(key=lambda x: x.score, reverse=True)

        logger.debug(f"[RAG][Retriever] Fusion complete. Filtered >= {self._threshold}: {len(filtered)} candidates left.")
        return filtered[:k]

    def retrieve_multi_namespace(self,
                                 query: str,
                                 user_id: str = "admin",
                                 namespaces: List[str] = None,
                                 top_k: int = None) -> List[RetrievedChunk]:
        """
        Search across multiple namespaces and merge results.
        """
        if namespaces is None:
            namespaces = ["knowledge", "documents", "episodic"]

        all_chunks = []
        for ns in namespaces:
            chunks = self.retrieve(query, user_id=user_id, namespace=ns,
                                   top_k=top_k or self._top_k)
            all_chunks.extend(chunks)

        all_chunks.sort(key=lambda x: x.score, reverse=True)
        k = top_k or self._top_k

        # Deduplicate by text content — keep only the highest-scoring copy
        seen_texts: set = set()
        deduped = []
        for c in all_chunks:
            key = c.text.strip()[:200]  # fingerprint on first 200 chars
            if key not in seen_texts:
                seen_texts.add(key)
                deduped.append(c)

        logger.debug(f"[RAG][Retriever] Multi-NS: {len(all_chunks)} raw → {len(deduped)} after dedup")
        return deduped[:k]


# ── Context formatter ──────────────────────────────────────────────────────────

def format_context_block(chunks: List[RetrievedChunk],
                         max_chars: int = 3000) -> str:
    """
    Converts retrieved chunks into a formatted [KNOWLEDGE CONTEXT] block
    suitable for injection into the system prompt.
    """
    if not chunks:
        return ""

    lines = ["\n### [KNOWLEDGE CONTEXT] ###",
             "The following information was retrieved from your long-term memory and knowledge base.",
             "Use it to answer the user's query accurately. Do NOT cite chunk numbers.\n"]

    total_chars = sum(len(line) + 1 for line in lines)
    for i, chunk in enumerate(chunks, 1):
        excerpt = chunk.text.strip()
        src_note = f" [from: {chunk.source}]" if chunk.source else ""
        entry = f"[{i}]{src_note} {excerpt}"
        if total_chars + len(entry) > max_chars:
            break
        lines.append(entry)
        total_chars += len(entry) + 1

    lines.append("### [END KNOWLEDGE CONTEXT] ###\n")
    return "\n".join(lines)
