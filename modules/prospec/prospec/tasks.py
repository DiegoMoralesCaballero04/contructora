import logging
from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutes


@shared_task(bind=True, soft_time_limit=75, time_limit=80)
def cercar_clients_osm_task(self, ubicacio: str, sector: str, paraules_clau: str, limit: int = 60):
    """
    Run OSM business search in a Celery worker to avoid blocking Gunicorn.
    Results cached in Redis with the task_id as key.
    """
    cache_key = f'prospec_osm_{self.request.id}'
    try:
        from modules.prospec.prospec import sources  # noqa — trigger registration
        from modules.prospec.prospec.sources_osm import font_osm_empreses
        resultats = font_osm_empreses(ubicacio, sector, paraules_clau, limit)
        cache.set(cache_key, {'ok': True, 'resultats': resultats, 'ubicacio': ubicacio}, CACHE_TTL)
        logger.info('OSM search "%s": %d results', ubicacio, len(resultats))
        return len(resultats)
    except Exception as exc:
        logger.error('OSM search task error: %s', exc)
        cache.set(cache_key, {'ok': False, 'error': str(exc)}, CACHE_TTL)
        raise
