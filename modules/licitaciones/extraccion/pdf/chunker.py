"""
Split large PDF texts into chunks that fit within LLM context windows.
For Llama 3 (8k context), we use chunks of ~6000 characters with overlap.
"""

CHUNK_SIZE = 6000
CHUNK_OVERLAP = 500


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Try to break at a paragraph boundary
        last_newline = chunk.rfind('\n\n')
        if last_newline > chunk_size // 2:
            chunk = chunk[:last_newline]
            end = start + last_newline

        chunks.append(chunk)
        start = end - overlap

    return chunks


def get_relevant_chunk(text: str, keywords: list[str] | None = None) -> str:
    """
    For very long documents, return the most relevant chunk based on keywords.
    Falls back to the first chunk if no keywords match.
    Default keywords target the sections with procurement criteria.
    """
    if not keywords:
        keywords = [
            'criteris d\'adjudicació', 'criterios de adjudicación',
            'fórmula', 'puntuació', 'puntuación',
            'pressupost', 'presupuesto', 'termini', 'plazo',
            'classificació', 'clasificación empresarial',
        ]

    chunks = chunk_text(text)
    if len(chunks) == 1:
        return chunks[0]

    # Score each chunk by keyword frequency
    scored = []
    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(kw.lower() in chunk_lower for kw in keywords)
        scored.append((score, chunk))

    # Return the highest-scoring chunk, or first if all score 0
    best_score, best_chunk = max(scored, key=lambda x: x[0])
    if best_score == 0:
        return chunks[0]
    return best_chunk
