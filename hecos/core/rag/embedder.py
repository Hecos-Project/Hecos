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


# ── Subprocess Embedder (Win32-safe) ──────────────────────────────────────────

class SubprocessEmbedder(BaseEmbedder):
    """
    Embedder che delega l'inferenza a un subprocess isolato (embedder_daemon.py).

    Motivo: fastembed/onnxruntime e Playwright (Chromium) condividono le Win32
    API per i thread pool nativi. Se entrambi girano nello stesso processo Python
    su Windows, ONNX Runtime crasha il processo dopo il primo uso.
    Questo embedder isola ONNX Runtime in un subprocess dedicato tramite JSON IPC,
    esattamente come Hecos fa già per Piper TTS.
    """

    _DIM_MAP = {
        "BAAI/bge-small-en-v1.5": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "BAAI/bge-base-en-v1.5": 768,
    }

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from hecos.core.rag.embedder_daemon import get_daemon
        self._daemon = get_daemon(model_name)
        self._model_name = model_name
        self._dim = self._DIM_MAP.get(model_name, 384)
        logger.info(f"[RAG][Embedder] SubprocessEmbedder creato per '{model_name}' (dim={self._dim}).")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        try:
            return self._daemon.embed(texts)
        except Exception as e:
            logger.error(f"[RAG][Embedder] SubprocessEmbedder embed_texts error: {e}")
            return [[0.0] * self._dim for _ in texts]

    def embed_text(self, text: str) -> List[float]:
        result = self.embed_texts([text])
        return result[0] if result else [0.0] * self._dim

    @property
    def dimension(self) -> int:
        # Aggiorna con la dimensione effettiva riportata dal daemon
        if self._daemon.dimension:
            return self._daemon.dimension
        return self._dim


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
    Factory che restituisce il miglior embedder disponibile.

    Priority:
      1. fastembed/onnx  → SubprocessEmbedder (isolato, Win32-safe con Playwright)
      2. sentence_transformers → SentenceTransformerEmbedder (torch-based)
      3. Fallback subprocess se ST non è installato
      4. StubEmbedder — no-op d'emergenza
    """
    # ── 1. FastEmbed (subprocess isolato) — SEMPRE preferito su Windows ──────
    #    Non usa FastEmbedEmbedder direttamente per evitare il crash onnx+Playwright.
    if embedder_type in ("fastembed", "onnx"):
        fastembed_model = _FASTEMBED_MODELS.get(model_name, model_name)
        try:
            return SubprocessEmbedder(fastembed_model)
        except Exception as e:
            logger.warning(f"[RAG][Embedder] SubprocessEmbedder non disponibile: {e}")

    # ── 2. SentenceTransformers (torch-based) ────────────────────────────────
    if embedder_type == "sentence_transformers":
        try:
            return SentenceTransformerEmbedder(model_name, device="cpu")
        except RuntimeError as e:
            logger.warning(f"[RAG][Embedder] SentenceTransformers unavailable: {e}")
        # Safety net: se ST non è installato, usa subprocess fastembed
        logger.warning(
            "[RAG][Embedder] sentence_transformers failed — subprocess fastembed come fallback."
        )
        fastembed_model = _FASTEMBED_MODELS.get(model_name, "BAAI/bge-small-en-v1.5")
        try:
            return SubprocessEmbedder(fastembed_model)
        except Exception as e:
            logger.warning(f"[RAG][Embedder] SubprocessEmbedder fallback fallito: {e}")

    # ── 3. Stub — il search non funzionerà ma il sistema resta vivo ──────────
    logger.error(
        "[RAG][Embedder] Tutti gli embedder reali hanno fallito. Uso StubEmbedder. "
        "Installa fastembed: pip install fastembed"
    )
    return StubEmbedder()
