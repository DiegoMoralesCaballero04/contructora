"""
Celery tasks for scraping contratacionesdelestado.es and downloading PDFs.
"""
import logging
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from .models import ScrapingJob
from .scrapers.contrataciones_scraper import ContratacionesScraper

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_licitaciones(self, filtres: dict | None = None, max_pagines: int = 10):
    """
    Main daily scraping task. Creates a ScrapingJob record, runs the scraper,
    persists results to PostgreSQL and raw data to MongoDB.
    """
    job = ScrapingJob.objects.create(
        estat=ScrapingJob.Estado.EN_CURS,
        filtres_aplicats=filtres or {},
    )
    logger.info('ScrapingJob #%d started', job.pk)

    try:
        scraper = ContratacionesScraper(filters=filtres)
        resultats = scraper.scrape(max_pages=max_pagines)

        job.total_trobades = len(resultats)
        noves = 0
        errors = 0

        for item in resultats:
            try:
                noves += _persist_licitacio(item)
            except Exception as e:
                logger.error('Failed to persist item %s: %s', item.get('expediente_id'), e)
                errors += 1

        job.noves_insertades = noves
        job.errors = errors
        job.estat = ScrapingJob.Estado.COMPLETAT
        logger.info('ScrapingJob #%d completed: %d new, %d errors', job.pk, noves, errors)

    except Exception as exc:
        job.estat = ScrapingJob.Estado.ERROR
        job.detalls_error = str(exc)
        logger.exception('ScrapingJob #%d failed: %s', job.pk, exc)
        raise self.retry(exc=exc)
    finally:
        job.finalitzat_en = timezone.now()
        job.save()

    return {'job_id': job.pk, 'noves': noves}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def download_pdf_licitacio(self, licitacio_pk: int):
    """
    Download the PDF plec for a licitacion and upload it to S3.
    Triggered automatically after a new licitacio is created.
    """
    from apps.licitaciones.models import Licitacion
    from storage.utils import upload_pdf_to_s3, generate_s3_key
    import httpx

    try:
        licitacio = Licitacion.objects.get(pk=licitacio_pk)
    except Licitacion.DoesNotExist:
        logger.error('Licitacio %d not found', licitacio_pk)
        return

    if licitacio.pdf_descargado or not licitacio.pdf_pliego_url:
        logger.debug('Licitacio %d: PDF already downloaded or no URL', licitacio_pk)
        return

    logger.info('Downloading PDF for licitacio %d: %s', licitacio_pk, licitacio.pdf_pliego_url)

    try:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            resp = client.get(licitacio.pdf_pliego_url)
            resp.raise_for_status()
            pdf_bytes = resp.content

        filename = f'plec_{licitacio.expediente_id}.pdf'
        s3_key = generate_s3_key(licitacio.expediente_id, filename)
        upload_pdf_to_s3(pdf_bytes, s3_key)

        licitacio.pdf_pliego_s3_key = s3_key
        licitacio.pdf_descargado = True
        licitacio.save(update_fields=['pdf_pliego_s3_key', 'pdf_descargado', 'actualizado_en'])

        logger.info('PDF uploaded to S3: %s', s3_key)

        # Trigger LLM extraction
        from apps.extraccion.tasks import extreure_dades_pdf
        extreure_dades_pdf.delay(licitacio_pk)

    except Exception as exc:
        logger.error('PDF download failed for licitacio %d: %s', licitacio_pk, exc)
        raise self.retry(exc=exc)


def _persist_licitacio(item: dict) -> int:
    """
    Persist a scraped item to PostgreSQL and MongoDB.
    Returns 1 if new record created, 0 if already existed.
    """
    from apps.licitaciones.models import Licitacion, Organismo
    from mongo.collections import raw_licitaciones

    expediente_id = item.get('expediente_id', '').strip()
    if not expediente_id:
        logger.warning('Item without expediente_id, skipping')
        return 0

    # Save raw data to MongoDB
    raw_doc = {**item, 'scraped_at': datetime.utcnow()}
    raw_doc.pop('raw_data', None)  # Avoid double nesting
    mongo_result = raw_licitaciones().replace_one(
        {'expediente_id': expediente_id},
        raw_doc,
        upsert=True,
    )

    # Skip if already in PostgreSQL
    if Licitacion.objects.filter(expediente_id=expediente_id).exists():
        return 0

    # Get or create organismo
    organismo = None
    if item.get('organismo_nombre'):
        organismo, _ = Organismo.objects.get_or_create(
            nombre=item['organismo_nombre'],
            defaults={'provincia': item.get('provincia', '')},
        )

    # Create licitacion
    Licitacion.objects.create(
        expediente_id=expediente_id,
        url_origen=item.get('url_origen', ''),
        titulo=item.get('titulo', ''),
        organismo=organismo,
        provincia=item.get('provincia', ''),
        municipio=item.get('municipio', ''),
        importe_base=item.get('importe_base'),
        importe_iva=item.get('importe_iva'),
        procedimiento=item.get('procedimiento', 'ABIERTO'),
        fecha_publicacion=_parse_date(item.get('fecha_publicacion')),
        fecha_limite_oferta=_parse_date(item.get('fecha_limite_oferta')),
        pdf_pliego_url=item.get('pdf_pliego_url', ''),
        mongo_id=str(mongo_result.upserted_id or ''),
    )
    return 1


def _parse_date(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(value)[:19], fmt)
        except ValueError:
            continue
    return None
