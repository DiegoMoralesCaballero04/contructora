import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def indexar_licitacio_task(self, licitacio_pk: int):
    try:
        from .embeddings import indexar_licitacio
        created = indexar_licitacio(licitacio_pk)
        logger.info('Indexació licitació %d: %d chunks creats', licitacio_pk, created)
        return created
    except Exception as exc:
        logger.error('Error indexant licitació %d: %s', licitacio_pk, exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def indexar_document_task(self, document_pk: str):
    try:
        from .embeddings import indexar_document
        created = indexar_document(document_pk)
        logger.info('Indexació document %s: %d chunks creats', document_pk, created)
        return created
    except Exception as exc:
        logger.error('Error indexant document %s: %s', document_pk, exc)
        raise self.retry(exc=exc)


@shared_task
def reindexar_tot():
    """Re-index all licitaciones that have an extraction but no embeddings yet."""
    from modules.licitaciones.licitaciones.models import Licitacion
    from .models import DocumentEmbedding

    indexades = set(
        DocumentEmbedding.objects.filter(font_tipus='EXTRACCION')
        .values_list('font_id', flat=True)
        .distinct()
    )

    qs = Licitacion.objects.filter(extraccion__isnull=False)
    total = 0
    for lit in qs.iterator(chunk_size=100):
        if str(lit.pk) not in indexades:
            indexar_licitacio_task.delay(lit.pk)
            total += 1

    logger.info('Llançades %d tasques de reindexació', total)
    return total
