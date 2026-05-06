"""
Embedding generation via Ollama (nomic-embed-text model).

Architecture:
  - nomic-embed-text produces 768-dim vectors optimized for retrieval.
  - Chunks are generated with overlap to preserve context at boundaries.
  - SHA-256 deduplication avoids re-embedding unchanged content.
  - Embeddings stored in PostgreSQL (JSON column now; migrate to pgvector later).
"""
import hashlib
import logging
from typing import List, Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

def _default_embed_model() -> str:
    try:
        from django.conf import settings as _s
        return getattr(_s, 'OLLAMA_EMBED_MODEL', 'nomic-embed-text')
    except Exception:
        return 'nomic-embed-text'

EMBED_MODEL = _default_embed_model()
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def generar_embedding(text: str, model: str = EMBED_MODEL) -> Optional[List[float]]:
    """
    Call Ollama /api/embeddings endpoint.
    Returns list of floats or None on failure.
    """
    try:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
        resp = httpx.post(url, json={'model': model, 'prompt': text}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data.get('embedding')
    except Exception as e:
        logger.error('Error generant embedding: %s', e)
        return None


def chunkar_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks, breaking at paragraph boundaries when possible.
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            break_at = text.rfind('\n\n', start, end)
            if break_at == -1:
                break_at = text.rfind('\n', start, end)
            if break_at == -1 or break_at <= start:
                break_at = end
            chunks.append(text[start:break_at].strip())
            start = max(break_at - overlap, start + 1)
        else:
            chunks.append(text[start:].strip())
            break
    return [c for c in chunks if c]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def indexar_licitacio(licitacio_pk: int):
    """
    Index a licitacion PDF and extraction data into the embedding store.
    Uses SHA-256 to skip unchanged chunks.
    """
    from modules.licitaciones.licitaciones.models import Licitacion
    from .models import DocumentEmbedding

    licitacio = Licitacion.objects.select_related('extraccion').get(pk=licitacio_pk)

    texts_to_index = []

    extraccion = getattr(licitacio, 'extraccion', None)
    if extraccion:
        meta_text = (
            f"Licitació: {licitacio.titol}\n"
            f"Expedient: {licitacio.expediente_id}\n"
            f"Organisme: {getattr(licitacio.organismo, 'nom', '')}\n"
            f"Import: {licitacio.importe_base}\n"
            f"Termini: {licitacio.fecha_limite_oferta}\n"
            f"Objecte: {extraccion.objecte}\n"
            f"Resum: {extraccion.resum_executiu}\n"
            f"Formula econòmica: {extraccion.formula_economica}\n"
            f"Classificació: {extraccion.classificacio_completa}"
        )
        texts_to_index.append(('EXTRACCION', meta_text))

    if licitacio.pdf_pliego_s3_key:
        try:
            from modules.licitaciones.extraccion.pdf.reader import extract_text_from_s3_pdf
            pdf_text = extract_text_from_s3_pdf(licitacio.pdf_pliego_s3_key)
            if pdf_text:
                texts_to_index.append(('LICITACIO', pdf_text))
        except Exception as e:
            logger.warning('No es pot indexar PDF de licitació %d: %s', licitacio_pk, e)

    created = 0
    for font_tipus, full_text in texts_to_index:
        chunks = chunkar_text(full_text)
        for i, chunk in enumerate(chunks):
            sha = sha256_text(chunk)
            if DocumentEmbedding.objects.filter(sha256_chunk=sha).exists():
                continue
            vector = generar_embedding(chunk)
            if vector is None:
                logger.warning('No es pot generar embedding per chunk %d de licitació %d', i, licitacio_pk)
                continue
            DocumentEmbedding.objects.update_or_create(
                font_tipus=font_tipus,
                font_id=str(licitacio_pk),
                numero_chunk=i,
                defaults={
                    'licitacio': licitacio,
                    'text_chunk': chunk,
                    'sha256_chunk': sha,
                    'embedding': vector,
                    'embedding_dim': len(vector),
                    'model_embedding': EMBED_MODEL,
                    'metadata': {
                        'titol': licitacio.titol,
                        'expediente_id': licitacio.expediente_id,
                    },
                },
            )
            created += 1

    logger.info('Indexats %d chunks per licitació %d', created, licitacio_pk)
    return created


def indexar_document(document_pk: str):
    """Index an internal document into the embedding store."""
    import uuid
    from modules.documents.documents.models import Document
    from modules.licitaciones.extraccion.pdf.reader import extract_text_from_s3_pdf
    from .models import DocumentEmbedding

    document = Document.objects.get(pk=uuid.UUID(str(document_pk)))
    if not document.s3_key or document.mime_type != 'application/pdf':
        return 0

    try:
        text = extract_text_from_s3_pdf(document.s3_key)
    except Exception as e:
        logger.error('Error llegint document %s: %s', document_pk, e)
        return 0

    chunks = chunkar_text(text)
    created = 0
    for i, chunk in enumerate(chunks):
        sha = sha256_text(chunk)
        if DocumentEmbedding.objects.filter(sha256_chunk=sha).exists():
            continue
        vector = generar_embedding(chunk)
        if not vector:
            continue
        DocumentEmbedding.objects.update_or_create(
            font_tipus='DOCUMENT',
            font_id=str(document_pk),
            numero_chunk=i,
            defaults={
                'document': document,
                'text_chunk': chunk,
                'sha256_chunk': sha,
                'embedding': vector,
                'embedding_dim': len(vector),
                'model_embedding': EMBED_MODEL,
                'metadata': {'nom': document.nom, 'categoria': document.categoria.codi},
            },
        )
        created += 1

    logger.info('Indexats %d chunks per document %s', created, document_pk)
    return created
