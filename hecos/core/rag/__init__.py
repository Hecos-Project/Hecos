"""
RAG Module — Public Facade
Hecos v0.26.0

Usage:
    from hecos.core.rag import get_rag_engine

    engine = get_rag_engine(config)
    engine.ingest_text("Some text...", source="notebook")
    context = engine.context_for_query("user query")
"""

from hecos.core.rag.engine import get_rag_engine, RAGEngine, STATUS_ONLINE, STATUS_STANDBY, STATUS_DEGRADED

__all__ = [
    "get_rag_engine",
    "RAGEngine",
    "STATUS_ONLINE",
    "STATUS_STANDBY",
    "STATUS_DEGRADED",
]
