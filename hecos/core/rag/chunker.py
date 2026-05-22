"""
MODULE: RAG Chunker
DESCRIPTION: Text splitting strategies for RAG ingestion pipeline.
             Three strategies available:
             - 'recursive'  : default, splits on paragraph then sentence
             - 'sentence'   : sentence-boundary aware splitter  
             - 'markdown'   : respects H1-H3 headers as natural chunk boundaries
"""

from __future__ import annotations
import re
from typing import List


class TextChunk:
    """A chunk of text with associated metadata."""

    __slots__ = ("text", "index", "source", "char_start")

    def __init__(self, text: str, index: int, source: str = "", char_start: int = 0):
        self.text = text.strip()
        self.index = index
        self.source = source
        self.char_start = char_start

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "chunk_index": self.index,
            "source": self.source,
            "char_start": self.char_start,
        }


# ── Base ───────────────────────────────────────────────────────────────────────

class BaseChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, source: str = "") -> List[TextChunk]:
        raise NotImplementedError


# ── Recursive character splitter ───────────────────────────────────────────────

class RecursiveChunker(BaseChunker):
    """
    Splits on double-newline (paragraphs), then single newline, then spaces.
    Merges short fragments back up to chunk_size, with overlap.
    """

    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def split(self, text: str, source: str = "") -> List[TextChunk]:
        if not text or not text.strip():
            return []
        chunks = self._split_recursive(text, self.SEPARATORS)
        merged = self._merge_chunks(chunks)
        return [TextChunk(t, i, source) for i, t in enumerate(merged) if t.strip()]

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        if not separators:
            return [text]
        sep = separators[0]
        parts = text.split(sep) if sep else list(text)
        result = []
        for part in parts:
            if len(part) > self.chunk_size:
                result.extend(self._split_recursive(part, separators[1:]))
            else:
                result.append(part)
        return result

    def _merge_chunks(self, parts: List[str]) -> List[str]:
        merged = []
        current = ""
        for part in parts:
            if len(current) + len(part) + 1 <= self.chunk_size:
                current = (current + " " + part).strip()
            else:
                if current:
                    merged.append(current)
                # Overlap: carry over tail of previous chunk
                if self.chunk_overlap > 0 and current:
                    overlap_text = current[-self.chunk_overlap:]
                    current = (overlap_text + " " + part).strip()
                else:
                    current = part.strip()
        if current:
            merged.append(current)
        return merged


# ── Sentence-aware splitter ────────────────────────────────────────────────────

class SentenceChunker(BaseChunker):
    """
    Splits text into sentences first, then groups them up to chunk_size.
    """
    _SENTENCE_END = re.compile(r'(?<=[.!?])\s+')

    def split(self, text: str, source: str = "") -> List[TextChunk]:
        if not text or not text.strip():
            return []
        sentences = self._SENTENCE_END.split(text.strip())
        chunks, current, idx = [], "", 0
        for sent in sentences:
            if len(current) + len(sent) + 1 <= self.chunk_size:
                current = (current + " " + sent).strip()
            else:
                if current:
                    chunks.append(TextChunk(current, idx, source))
                    idx += 1
                    # overlap
                    if self.chunk_overlap > 0:
                        current = current[-self.chunk_overlap:] + " " + sent
                    else:
                        current = sent.strip()
                else:
                    current = sent.strip()
        if current.strip():
            chunks.append(TextChunk(current, idx, source))
        return chunks


# ── Markdown splitter ──────────────────────────────────────────────────────────

class MarkdownChunker(BaseChunker):
    """
    Uses markdown headers (H1, H2, H3) as primary split boundaries.
    Falls back to RecursiveChunker for sections exceeding chunk_size.
    """
    _HEADER = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)

    def split(self, text: str, source: str = "") -> List[TextChunk]:
        if not text or not text.strip():
            return []
        positions = [(m.start(), m.group(0)) for m in self._HEADER.finditer(text)]
        if not positions:
            return RecursiveChunker(self.chunk_size, self.chunk_overlap).split(text, source)

        sections = []
        for i, (start, header) in enumerate(positions):
            end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            sections.append(text[start:end].strip())

        rc = RecursiveChunker(self.chunk_size, self.chunk_overlap)
        chunks, global_idx = [], 0
        for section in sections:
            sub = rc.split(section, source)
            for c in sub:
                c.index = global_idx
                global_idx += 1
                chunks.append(c)
        return chunks


# ── Factory ────────────────────────────────────────────────────────────────────

def get_chunker(strategy: str = "recursive",
                chunk_size: int = 512,
                chunk_overlap: int = 64) -> BaseChunker:
    mapping = {
        "recursive": RecursiveChunker,
        "sentence":  SentenceChunker,
        "markdown":  MarkdownChunker,
    }
    cls = mapping.get(strategy, RecursiveChunker)
    return cls(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
