"""
RAG retriever: cosine similarity search over stored embeddings.

Architecture:
  Current: in-Python cosine similarity (works without pgvector).
  Production upgrade path:
    1. Install pgvector: pip install pgvector
    2. Run: CREATE EXTENSION IF NOT EXISTS vector;
    3. Migrate embedding field to VectorField
    4. Replace _cosine_search with:
         DocumentEmbedding.objects.order_by(L2Distance('embedding', query_vec))[:top_k]
       for true index-accelerated ANN search (IVFFlat or HNSW).

For datasets < 50k embeddings, in-Python is fast enough (~100ms at 10k docs).
"""
import logging
import math
from typing import List, Optional

logger = logging.getLogger(__name__)


def generar_context_bbdd() -> str:
    """
    Query the application database and return a natural-language summary
    that the LLM can use to answer questions about application data.
    Each module is guarded independently so missing modules don't break the RAG.
    """
    parts = []

    try:
        from modules.licitaciones.licitaciones.models import Licitacion
        total = Licitacion.objects.count()
        noves = Licitacion.objects.filter(estado=Licitacion.Estado.NUEVA).count()
        en_prep = Licitacion.objects.filter(estado=Licitacion.Estado.EN_PREPARACION).count()
        presentades = Licitacion.objects.filter(estado=Licitacion.Estado.PRESENTADA).count()
        adjudicades = Licitacion.objects.filter(estado=Licitacion.Estado.ADJUDICADA).count()
        parts.append(
            f"LICITACIONS: {total} en total. "
            f"{noves} noves, {en_prep} en preparació, {presentades} presentades, {adjudicades} adjudicades."
        )
        from django.db.models import Sum
        import_total = Licitacion.objects.filter(es_relevante=True).aggregate(
            t=Sum('importe_base'))['t'] or 0
        parts.append(f"Import total licitacions rellevants: {import_total:,.0f} €.")
    except Exception:
        pass

    try:
        from modules.marketing.marketing.models import EmpresaProspect
        total_p = EmpresaProspect.objects.count()
        clients = EmpresaProspect.objects.filter(estat=EmpresaProspect.Estat.CLIENT).count()
        interessats = EmpresaProspect.objects.filter(estat=EmpresaProspect.Estat.INTERESSAT).count()
        prospects = EmpresaProspect.objects.filter(estat=EmpresaProspect.Estat.PROSPECCIO).count()
        parts.append(
            f"PROSPECTS/CRM: {total_p} empreses prospecte. "
            f"{clients} clients, {interessats} interessats, {prospects} en prospecció."
        )
    except Exception:
        pass

    try:
        from modules.ofertes.ofertes.models import Oferta
        total_o = Oferta.objects.count()
        guanyades = Oferta.objects.filter(estat=Oferta.Estat.GUANYADA).count()
        enviades = Oferta.objects.filter(estat=Oferta.Estat.ENVIADA).count()
        parts.append(
            f"OFERTES: {total_o} en total. {guanyades} guanyades, {enviades} enviades."
        )
    except Exception:
        pass

    try:
        from modules.rrhh.rrhh.models import UserProfile
        from django.contrib.auth.models import User
        total_users = User.objects.filter(is_active=True).count()
        parts.append(f"USUARIS: {total_users} usuaris actius al sistema.")
    except Exception:
        pass

    try:
        from modules.erp.erp.models import Factura
        from django.db.models import Sum as _Sum
        total_f = Factura.objects.count()
        import_facturat = Factura.objects.aggregate(t=_Sum('total'))['t'] or 0
        parts.append(f"ERP FACTURES: {total_f} factures. Total facturat: {import_facturat:,.2f} €.")
    except Exception:
        pass

    if not parts:
        return ''

    return (
        "DADES DE L'APLICACIÓ (extret de la base de dades en temps real):\n"
        + "\n".join(f"- {p}" for p in parts)
    )


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def recuperar_context(
    pregunta: str,
    top_k: int = 5,
    filtres: Optional[dict] = None,
    similitud_minima: float = 0.30,
) -> List[dict]:
    """
    Main retrieval function.
    1. Embed the question with the same model used for indexing.
    2. Compute cosine similarity against all stored embeddings.
    3. Return top_k results above minimum similarity.

    filtres keys: font_tipus, licitacio_id, document_id
    """
    from .embeddings import generar_embedding
    from .models import DocumentEmbedding

    query_vec = generar_embedding(pregunta)
    if not query_vec:
        logger.error('No s\'ha pogut generar embedding per la pregunta')
        return []

    qs = DocumentEmbedding.objects.all()
    if filtres:
        if ft := filtres.get('font_tipus'):
            qs = qs.filter(font_tipus=ft)
        if lid := filtres.get('licitacio_id'):
            qs = qs.filter(licitacio_id=lid)
        if did := filtres.get('document_id'):
            qs = qs.filter(document_id=did)

    qs = qs.only('id', 'font_tipus', 'font_id', 'numero_chunk', 'text_chunk', 'embedding', 'metadata')

    scored = []
    for emb in qs.iterator(chunk_size=500):
        if not emb.embedding:
            continue
        sim = cosine_similarity(query_vec, emb.embedding)
        if sim >= similitud_minima:
            scored.append({
                'embedding_id': str(emb.id),
                'font_tipus': emb.font_tipus,
                'font_id': emb.font_id,
                'numero_chunk': emb.numero_chunk,
                'text': emb.text_chunk,
                'similitud': round(sim, 4),
                'metadata': emb.metadata,
            })

    scored.sort(key=lambda x: x['similitud'], reverse=True)
    return scored[:top_k]


def construir_prompt_rag(pregunta: str, chunks: List[dict], context_bbdd: str = '', idioma: str = 'es') -> str:
    """Build a RAG prompt injecting document context and optional live DB context."""
    lang_instruction = {
        'ca': 'Respon SEMPRE en català/valencià, independentment de l\'idioma de la pregunta.',
        'es': 'Responde SIEMPRE en español, independientemente del idioma de la pregunta.',
        'en': 'ALWAYS respond in English, regardless of the language of the question.',
    }.get(idioma, 'Responde en español.')

    context_parts = []
    for i, c in enumerate(chunks, 1):
        meta = c.get('metadata', {})
        font_label = meta.get('titol', c.get('font_id', ''))
        context_parts.append(f'[Font {i}: {font_label}]\n{c["text"]}')

    context_docs = '\n\n---\n\n'.join(context_parts)

    sections = []
    if context_docs:
        sections.append(f'DOCUMENTS INDEXATS:\n{context_docs}')
    if context_bbdd:
        sections.append(context_bbdd)

    context = '\n\n'.join(sections) if sections else 'Sin contexto disponible.'

    return f"""Ets un assistent expert en licitacions públiques i gestió de la construcció a Espanya.
Tens accés a documents indexats i a dades en temps real de l'aplicació.
{lang_instruction}
Respon basant-te en el context proporcionat. Si el context no conté informació suficient, indica-ho clarament.

CONTEXT:
{context}

PREGUNTA:
{pregunta}

RESPOSTA:"""
