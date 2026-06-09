"""
MODULE: RAG Embedder
DESCRIPTION: Adapter layer for text embedding models.
             Embedding priority:
               1. FastEmbedEmbedder  — ONNX Runtime, CPU-native, no torch required (RECOMMENDED)
               2. SentenceTransformerEmbedder — GPU/CPU, requires torch + transformers
               3. StubEmbedder      — fallback no-op (search will NOT work correctly)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from hecos.core.logging import logger


class BaseEmbedder(ABC):
    """Abstract embedding interface. All embedders must implement `embed_texts`."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Return a list of embedding vectors (one per input text)."""

    def embed_text(self, text: str) -> List[float]:
        """Convenience wrapper for a single text."""
        return self.embed_texts([text])[0]

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""


# ── FastEmbed (ONNX Runtime) embedder — Enterprise default ────────────────────

class FastEmbedEmbedder(BaseEmbedder):
    """
    Production embedder using fastembed (Qdrant library).
    Uses ONNX Runtime internally — zero PyTorch dependency.
    Works on any hardware: CPU (Intel/AMD/ARM) or GPU via onnxruntime-gpu.

    Supported model IDs:
      - "BAAI/bge-small-en-v1.5"               (384-dim, fast, multilingual)
      - "sentence-transformers/all-MiniLM-L6-v2" (384-dim, balanced)
      - "BAAI/bge-base-en-v1.5"                (768-dim, higher quality)
    """

    _MODEL_DIMS = {
        "all-MiniLM-L6-v2": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
    }

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        try:
            import os
            # Prevent Rust tokenizers from deadlocking when initialized in a background thread
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            from fastembed import TextEmbedding
            # Force threads=1 to prevent ONNX Runtime from spawning nested thread pools
            # which can cause hard crashes or hangs on Windows in multi-threaded apps like Hecos.
            self._model = TextEmbedding(model_name=model_name, threads=1)
            self._model_name = model_name
            self._dim = self._MODEL_DIMS.get(model_name, 384)
            logger.info(f"[RAG][Embedder] FastEmbed (ONNX/CPU) loaded: {model_name} (dim={self._dim})")
        except Exception as e:
            raise RuntimeError(f"[RAG][Embedder] FastEmbed failed to load '{model_name}': {e}") from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            # fastembed.embed() returns a generator of numpy arrays
            results = list(self._model.embed(texts))
            return [r.tolist() for r in results]
        except Exception as e:
            logger.error(f"[RAG][Embedder] FastEmbed embed_texts error: {e}")
            # Fallback to zeros only if something goes catastrophically wrong mid-run
            return [[0.0] * self._dim for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dim


# ── SentenceTransformer embedder (GPU-capable fallback) ───────────────────────

class SentenceTransformerEmbedder(BaseEmbedder):
    """
    GPU-accelerated embedder using sentence-transformers.
    Requires: pip install sentence-transformers torch>=2.0
    """

    _MODEL_DIMS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-multilingual-MiniLM-L12-v2": 384,
        "BAAI/bge-small-en-v1.5": 384,
    }

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name, device=device)
            self._model_name = model_name
            self._dim = self._MODEL_DIMS.get(model_name, 384)
            logger.info(f"[RAG][Embedder] SentenceTransformer loaded: {model_name} on {device} (dim={self._dim})")
        except Exception as e:
            raise RuntimeError(f"[RAG][Embedder] SentenceTransformer failed to load '{model_name}': {e}") from e

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return vecs.tolist()
        except Exception as e:
            logger.error(f"[RAG][Embedder] embed_texts error: {e}")
            return [[0.0] * self._dim for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dim


# ── Stub (non-functional) embedder ────────────────────────────────────────────

class StubEmbedder(BaseEmbedder):
    """
    Last-resort fallback. Produces random unit vectors.
    WARNING: Semantic search will NOT work correctly with this embedder.
             Install `fastembed` to get real embeddings.
    """
    _DIM = 384

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        logger.warning(
            "[RAG][Embedder] ⚠️  StubEmbedder is active — search results are MEANINGLESS. "
            "Run: pip install fastembed"
        )
        import random
        vecs = []
        for _ in texts:
            v = [random.uniform(-1.0, 1.0) for _ in range(self._DIM)]
            norm = sum(x * x for x in v) ** 0.5
            vecs.append([x / norm for x in v])
        return vecs

    @property
    def dimension(self) -> int:
        return self._DIM


# ── Factory ────────────────────────────────────────────────────────────────────

_FASTEMBED_MODELS = {
    # Legacy key → fastembed model ID map
    "all-MiniLM-L6-v2":               "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-small-en-v1.5":         "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5":          "BAAI/bge-base-en-v1.5",
}


def get_embedder(embedder_type: str = "fastembed",
                 model_name: str = "BAAI/bge-small-en-v1.5") -> BaseEmbedder:
    """
    Factory that returns the best available embedder.

    Priority:
      1. fastembed  — preferred: ONNX CPU, no torch needed (tried first always)
      2. sentence_transformers — GPU-capable but needs torch ≥ 2.0
      3. fastembed safety net — if embedder_type=sentence_transformers but ST fails
      4. StubEmbedder — emergency no-op fallback
    """
    # ── 1. FastEmbed (ONNX Runtime) — preferred ──────────────────────────────
    if embedder_type in ("fastembed", "onnx"):
        fastembed_model = _FASTEMBED_MODELS.get(model_name, model_name)
        try:
            return FastEmbedEmbedder(fastembed_model)
        except RuntimeError as e:
            logger.warning(f"[RAG][Embedder] FastEmbed unavailable, trying sentence-transformers: {e}")

    # ── 2. SentenceTransformers (torch-based) ────────────────────────────────
    if embedder_type in ("sentence_transformers", "fastembed"):
        try:
            return SentenceTransformerEmbedder(model_name, device="cpu")
        except RuntimeError as e:
            logger.warning(f"[RAG][Embedder] SentenceTransformers unavailable: {e}")

    # ── 3. Safety net: if ST was requested but failed, try fastembed anyway ──
    if embedder_type == "sentence_transformers":
        logger.warning(
            "[RAG][Embedder] sentence_transformers failed — attempting fastembed as safety fallback."
        )
        fastembed_model = _FASTEMBED_MODELS.get(model_name, "BAAI/bge-small-en-v1.5")
        try:
            return FastEmbedEmbedder(fastembed_model)
        except RuntimeError as e:
            logger.warning(f"[RAG][Embedder] FastEmbed safety fallback also failed: {e}")

    # ── 4. Stub — search won't work but system boots ──────────────────────────
    logger.error(
        "[RAG][Embedder] All real embedders failed. Using StubEmbedder. "
        "Install fastembed: pip install fastembed"
    )
    return StubEmbedder()
