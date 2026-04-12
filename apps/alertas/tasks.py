import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def enviar_alerta_nova_licitacio(licitacio_pk: int):
    """Send alerts for a new licitacion to all configured users."""
    from apps.licitaciones.models import Licitacion
    from apps.alertas.models import AlertaConfig
    from apps.alertas.channels.email import enviar_email_nova_licitacio
    from apps.alertas.channels.telegram import enviar_telegram, missatge_nova_licitacio

    try:
        licitacio = Licitacion.objects.get(pk=licitacio_pk)
    except Licitacion.DoesNotExist:
        return

    configs = AlertaConfig.objects.filter(activa=True).select_related('usuari')

    for config in configs:
        # Apply user filters
        if config.importe_max and licitacio.importe_base:
            if licitacio.importe_base > config.importe_max:
                continue
        if config.provincies and licitacio.provincia not in config.provincies:
            continue

        # Email
        if config.email_actiu and config.usuari.email:
            enviar_email_nova_licitacio(config.usuari.email, licitacio)

        # Telegram
        if config.telegram_actiu and settings.TELEGRAM_CHAT_ID:
            msg = missatge_nova_licitacio(licitacio)
            enviar_telegram(settings.TELEGRAM_CHAT_ID, msg)

    # Also trigger PDF download now that we know it's relevant
    from apps.scraping.tasks import download_pdf_licitacio
    if licitacio.pdf_pliego_url and not licitacio.pdf_descargado:
        download_pdf_licitacio.delay(licitacio_pk)


@shared_task
def enviar_resum_diari():
    """Send daily digest to all active alert configs. Scheduled at 08:00."""
    from django.utils import timezone
    from apps.licitaciones.models import Licitacion
    from apps.alertas.models import AlertaConfig
    from apps.alertas.channels.email import enviar_resum_diari
    from apps.alertas.channels.telegram import enviar_telegram, missatge_resum_diari

    avui = timezone.now().date()
    licitacions_avui = list(
        Licitacion.objects.filter(creado_en__date=avui, es_relevante=True)
        .select_related('organismo')
        .order_by('-importe_base')
    )

    if not licitacions_avui:
        logger.info('No new licitaciones today, skipping digest')
        return

    configs = AlertaConfig.objects.filter(activa=True).select_related('usuari')
    for config in configs:
        if config.email_actiu and config.usuari.email:
            enviar_resum_diari(config.usuari.email, licitacions_avui, avui)

        if config.telegram_actiu and settings.TELEGRAM_CHAT_ID:
            msg = missatge_resum_diari(licitacions_avui, avui)
            enviar_telegram(settings.TELEGRAM_CHAT_ID, msg)

    logger.info('Daily digest sent: %d licitaciones', len(licitacions_avui))
