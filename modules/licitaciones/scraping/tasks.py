import logging
from datetime import datetime

from celery import shared_task
from django.utils import timezone

from .models import ScrapingJob, ScrapingTemplate
from .scrapers.contrataciones_scraper import ContratacionesScraper

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_licitaciones(self, filtres: dict | None = None, max_pagines: int | None = None, template_id: int | None = None):
    """
    Main daily scraping task. Uses the single ScrapingTemplate.
    Inline filtres override template filters.
    template_id parameter is ignored (kept for backward compatibility).
    """
    template = ScrapingTemplate.get_singleton()

    effective_filters = template.to_filters()
    effective_max_pagines = max_pagines or template.max_pagines

    if filtres:
        if 'provincia' in filtres and 'provincies' not in filtres:
            filtres = {**filtres, 'provincies': [filtres.pop('provincia')]}
        effective_filters.update(filtres)

    job = ScrapingJob.objects.create(
        template=template,
        estat=ScrapingJob.Estado.EN_CURS,
        filtres_aplicats=effective_filters,
    )
    logger.info('ScrapingJob #%d started (template=%s)', job.pk, template.pk)

    try:
        scraper = ContratacionesScraper(filters=effective_filters)
        resultats = scraper.scrape(max_pages=effective_max_pagines)

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
    from modules.licitaciones.licitaciones.models import Licitacion
    from core.storage.utils import upload_pdf_to_s3, generate_s3_key
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

        try:
            from modules.licitaciones.extraccion.tasks import extreure_dades_pdf
            extreure_dades_pdf.delay(licitacio_pk)
        except ImportError:
            pass

    except Exception as exc:
        logger.error('PDF download failed for licitacio %d: %s', licitacio_pk, exc)
        raise self.retry(exc=exc)


def _persist_licitacio(item: dict) -> int:
    """
    Persist a scraped item to PostgreSQL and MongoDB.
    Returns 1 if new record created, 0 if already existed or deadline passed.
    """
    from modules.licitaciones.licitaciones.models import Licitacion, Organismo
    from core.mongo.collections import raw_licitaciones

    expediente_id = item.get('expediente_id', '').strip()
    if not expediente_id:
        logger.warning('Item without expediente_id, skipping')
        return 0

    fecha_limite = _parse_date(item.get('fecha_limite_oferta'))
    if fecha_limite and fecha_limite < timezone.now():
        logger.debug('Item %s deadline passed, skipping', expediente_id)
        return 0

    raw_doc = {**item, 'scraped_at': datetime.utcnow()}
    raw_doc.pop('raw_data', None)
    mongo_result = raw_licitaciones().replace_one(
        {'expediente_id': expediente_id},
        raw_doc,
        upsert=True,
    )

    if Licitacion.objects.filter(expediente_id=expediente_id).exists():
        return 0

    organismo = None
    if item.get('organismo_nombre'):
        organismo, _ = Organismo.objects.get_or_create(
            nombre=item['organismo_nombre'],
            defaults={'provincia': item.get('provincia', '')},
        )

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
        fecha_limite_oferta=fecha_limite,
        pdf_pliego_url=item.get('pdf_pliego_url', ''),
        mongo_id=str(mongo_result.upserted_id or ''),
    )
    return 1


def _parse_date(value):
    if not value:
        return None
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            naive = datetime.strptime(str(value)[:19], fmt)
            return timezone.make_aware(naive, timezone.get_current_timezone())
        except ValueError:
            continue
    return None
