"""
Celery tasks for LLM-based PDF data extraction.
"""
import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def extreure_dades_pdf(self, licitacio_pk: int):
    """
    Full extraction pipeline:
    1. Load PDF text from S3
    2. Find the most relevant chunk
    3. Send to Ollama for structured extraction
    4. Parse the JSON response
    5. Save to PostgreSQL + MongoDB
    6. Generate executive summary
    """
    from apps.licitaciones.models import Licitacion
    from apps.extraccion.models import Extraccion
    from apps.extraccion.ollama.client import OllamaClient
    from apps.extraccion.ollama.prompts import ACTIVE_EXTRACTION_PROMPT, SUMMARY_PROMPT
    from apps.extraccion.ollama.response_parser import parse_extraction_response
    from apps.extraccion.pdf.reader import extract_text_from_s3_pdf
    from apps.extraccion.pdf.chunker import get_relevant_chunk
    from mongo.collections import llm_responses, pdf_chunks
    from django.conf import settings

    try:
        licitacio = Licitacion.objects.get(pk=licitacio_pk)
    except Licitacion.DoesNotExist:
        logger.error('Licitacio %d not found', licitacio_pk)
        return

    extraccion, _ = Extraccion.objects.get_or_create(licitacio=licitacio)
    extraccion.estat = Extraccion.Estado.EN_CURS
    extraccion.intents += 1
    extraccion.model_usat = settings.OLLAMA_MODEL
    extraccion.save(update_fields=['estat', 'intents', 'model_usat'])

    try:
        # 1. Extract PDF text
        if not licitacio.pdf_pliego_s3_key:
            raise ValueError('No S3 key for PDF')

        pdf_text = extract_text_from_s3_pdf(licitacio.pdf_pliego_s3_key)
        if not pdf_text.strip():
            raise ValueError('PDF text is empty after extraction')

        # Save chunks to MongoDB
        pdf_chunks().insert_one({
            'licitacio_pk': licitacio_pk,
            'expediente_id': licitacio.expediente_id,
            'full_text_length': len(pdf_text),
            'extracted_at': timezone.now(),
        })

        # 2. Find the most relevant text chunk for extraction
        relevant_chunk = get_relevant_chunk(pdf_text)

        # 3. Build prompt and call Ollama
        client = OllamaClient()
        prompt = ACTIVE_EXTRACTION_PROMPT.format(text=relevant_chunk)
        raw_response = client.generate(prompt)

        # Save raw LLM response to MongoDB
        llm_doc = {
            'licitacio_pk': licitacio_pk,
            'expediente_id': licitacio.expediente_id,
            'prompt': prompt,
            'raw_response': raw_response,
            'model': settings.OLLAMA_MODEL,
            'prompt_version': 'v1',
            'timestamp': timezone.now(),
        }
        mongo_result = llm_responses().insert_one(llm_doc)

        # 4. Parse the response
        parsed = parse_extraction_response(raw_response)
        if not parsed['success']:
            extraccion.estat = Extraccion.Estado.ERROR
            extraccion.error_msg = parsed['error']
            extraccion.mongo_extraccion_id = str(mongo_result.inserted_id)
            extraccion.save()
            return

        data = parsed['data']

        # 5. Generate executive summary
        summary_prompt = SUMMARY_PROMPT.format(text=relevant_chunk[:3000])
        resum = client.generate(summary_prompt, timeout=60)

        # 6. Save to PostgreSQL
        _update_licitacio_from_extraction(licitacio, data)

        extraccion.objecte_extret = data.get('objecte', '')
        extraccion.pressupost_extret = data.get('pressupost_base')
        extraccion.termini_mesos = data.get('termini_execucio_mesos')
        extraccion.formula_economica = data.get('formula_economica', '')
        extraccion.requereix_declaracio = data.get('requereix_declaracio_responsable')
        extraccion.resum_executiu = resum.strip()
        extraccion.estat = Extraccion.Estado.OK
        extraccion.error_msg = ''
        extraccion.mongo_extraccion_id = str(mongo_result.inserted_id)

        grup = data.get('classificacio_grup', '')
        sub = data.get('classificacio_subgrup', '')
        cat = data.get('classificacio_categoria', '')
        if grup:
            extraccion.classificacio_completa = f'{grup}{sub}{cat}'

        if data.get('data_limit_ofertes'):
            try:
                extraccion.data_limit = date.fromisoformat(data['data_limit_ofertes'])
            except ValueError:
                pass

        extraccion.save()
        logger.info('Extraction OK for licitacio %d', licitacio_pk)

    except Exception as exc:
        logger.exception('Extraction failed for licitacio %d: %s', licitacio_pk, exc)
        extraccion.estat = Extraccion.Estado.ERROR
        extraccion.error_msg = str(exc)
        extraccion.save(update_fields=['estat', 'error_msg', 'actualitzada_en'])
        raise self.retry(exc=exc)


@shared_task
def reextreure_pendents():
    """Retry extraction for all licitaciones without a successful extraction."""
    from apps.licitaciones.models import Licitacion
    from apps.extraccion.models import Extraccion

    sense_extraccion = Licitacion.objects.filter(
        pdf_descargado=True,
        extraccion__isnull=True,
    )
    for licitacio in sense_extraccion:
        extreure_dades_pdf.delay(licitacio.pk)

    errors = Extraccion.objects.filter(estat=Extraccion.Estado.ERROR, intents__lt=3)
    for extraccion in errors:
        extreure_dades_pdf.delay(extraccion.licitacio_id)

    return {'reintentades': errors.count() + sense_extraccion.count()}


def _update_licitacio_from_extraction(licitacio, data: dict):
    """Update licitacion fields with extracted data if they were empty."""
    changed = False
    if not licitacio.plazo_ejecucion_dias and data.get('termini_execucio_dies'):
        licitacio.plazo_ejecucion_dias = data['termini_execucio_dies']
        changed = True
    if not licitacio.clasificacion_grupo and data.get('classificacio_grup'):
        licitacio.clasificacion_grupo = data['classificacio_grup']
        licitacio.clasificacion_subgrupo = data.get('classificacio_subgrup', '')
        licitacio.clasificacion_categoria = data.get('classificacio_categoria', '')
        changed = True
    if changed:
        licitacio.save(update_fields=[
            'plazo_ejecucion_dias', 'clasificacion_grupo',
            'clasificacion_subgrupo', 'clasificacion_categoria', 'actualizado_en',
        ])
