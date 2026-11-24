import re

text = "[excited] Zero moral filters. Zero social bias. Zero political agendas. [whisper] From the core engine to every single module, Hecos is built on one unshakeable rule: freedom of thought belongs to everyone... [laughing] though we strongly encourage actually using your own brain instead of renting someone else's."

print(f"Len: {len(text)} chars")
print()

# INLINE_TAG_RE as used in tag_processor.py
INLINE_TAG_RE = re.compile(r'\[(?!pause\b|silence\b)([^\]]{1,40})\]', re.IGNORECASE)

def parse_pause_duration(tag: str):
    """Returns seconds if tag is a pause, else None."""
    m = re.match(r'^\[(?:pause|silence)[:\s]*([\d.]+)\s*(?:s|sec|seconds?)?\s*\]$', tag, re.IGNORECASE)
    if m:
        return float(m.group(1))
    if re.match(r'^\[(?:pause|silence)\]$', tag, re.IGNORECASE):
        return 0.5
    return None

tags = list(INLINE_TAG_RE.finditer(text))
print(f"Tags found: {len(tags)}")
for t in tags:
    print(f"  {t.group(0)!r} at pos {t.start()}-{t.end()}")

print()
has_non_pause = any(parse_pause_duration(m.group(0)) is None for m in INLINE_TAG_RE.finditer(text))
print(f"has_non_pause_tags: {has_non_pause}")

starts_with_tag = bool(re.match(r'^\s*\[[^\]]+\]', text))
print(f"Starts with tag (_LEADING_TAG_RE): {starts_with_tag}")
print()

# Simulate chunk_length=200 splitting by Fish Speech internals
# Fish Speech splits at chunk_length boundaries (by sentence)
chunk_length = 200
print(f"=== If Fish chunk_length={chunk_length}, text would be split at sentence boundaries ===")
# Rough approximation: Fish splits on sentence-ending punctuation within chunk_length
sentences = re.split(r'(?<=[.!?])\s+', text)
chunks = []
current = ""
for s in sentences:
    if current and len(current) + len(s) + 1 > chunk_length:
        chunks.append(current.strip())
        current = s
    else:
        current = (current + " " + s).strip() if current else s
if current:
    chunks.append(current.strip())

print(f"Approximate Fish-internal chunks ({len(chunks)}):")
for i, c in enumerate(chunks):
    print(f"  [{i+1}] ({len(c)} chars) {c[:80]}...")
    tags_in_chunk = list(INLINE_TAG_RE.finditer(c))
    print(f"       Tags: {[m.group(0) for m in tags_in_chunk]}")
