import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def sincronitzar_esdeveniment(esdeveniment_pk: int):
    """Push a single calendar event to Microsoft Calendar."""
    try:
        from .models import Esdeveniment, CalendariConfig
        from .microsoft import MicrosoftGraphClient

        esdev = Esdeveniment.objects.select_related('creador', 'licitacio', 'oferta').get(
            pk=esdeveniment_pk
        )
        try:
            config = esdev.creador.calendari_config
        except CalendariConfig.DoesNotExist:
            logger.debug('Usuari %s sense config calendari, saltant', esdev.creador.username)
            return

        if not config.esta_connectat:
            return

        client = MicrosoftGraphClient(config)
        payload = MicrosoftGraphClient.build_event_payload(esdev)
        payload['subject'] = esdev.titol

        if esdev.ms_event_id:
            client.update_event(esdev.ms_event_id, payload)
        else:
            result = client.create_event(payload)
            esdev.ms_event_id = result.get('id', '')

        esdev.estat = Esdeveniment.Estat.SINCRONIT
        esdev.error_msg = ''
        esdev.save(update_fields=['ms_event_id', 'estat', 'error_msg', 'actualitzada_en'])

    except Exception as exc:
        logger.error('Error sincronitzant esdeveniment %d: %s', esdeveniment_pk, exc)
        from .models import Esdeveniment
        Esdeveniment.objects.filter(pk=esdeveniment_pk).update(
            estat=Esdeveniment.Estat.ERROR,
            error_msg=str(exc),
        )


@shared_task
def crear_esdeveniments_licitacio(licitacio_pk: int, usuari_pk: int):
    """
    Auto-creates calendar events from a licitacion's key dates.
    Creates: deadline event + internal review meeting 5 days before.
    """
    try:
        from modules.licitaciones.licitaciones.models import Licitacion
        from django.contrib.auth.models import User
        from .models import Esdeveniment
        import datetime

        licitacio = Licitacion.objects.get(pk=licitacio_pk)
        user = User.objects.get(pk=usuari_pk)

        events_created = []

        if licitacio.fecha_limite_oferta:
            deadline = licitacio.fecha_limite_oferta
            esdev = Esdeveniment.objects.get_or_create(
                licitacio=licitacio,
                tipus=Esdeveniment.TipusEsdeveniment.TERMINI_LICITACIO,
                defaults={
                    'creador': user,
                    'titol': f'Termini: {licitacio.titol[:80]}',
                    'descripcio': f'Data límit presentació oferta.\nExpedient: {licitacio.expediente_id}',
                    'inici': deadline,
                    'fi': deadline + datetime.timedelta(hours=1),
                    'recordatori_minuts': 1440,
                },
            )[0]
            events_created.append(esdev.pk)

            review_date = deadline - datetime.timedelta(days=5)
            if review_date > timezone.now():
                esdev_rev = Esdeveniment.objects.get_or_create(
                    licitacio=licitacio,
                    tipus=Esdeveniment.TipusEsdeveniment.REUNIO_INTERNA,
                    defaults={
                        'creador': user,
                        'titol': f'Revisió oferta: {licitacio.titol[:60]}',
                        'descripcio': f'Reunió interna per revisar i aprovar l\'oferta.\nExpedient: {licitacio.expediente_id}',
                        'inici': review_date.replace(hour=10, minute=0, second=0, microsecond=0),
                        'fi': review_date.replace(hour=11, minute=0, second=0, microsecond=0),
                        'recordatori_minuts': 60,
                    },
                )[0]
                events_created.append(esdev_rev.pk)

        for pk in events_created:
            sincronitzar_esdeveniment.delay(pk)

        logger.info('Creats %d esdeveniments per licitació %d', len(events_created), licitacio_pk)

    except Exception as exc:
        logger.error('Error creant esdeveniments per licitació %d: %s', licitacio_pk, exc)


@shared_task
def sincronitzar_events_pendents():
    """Hourly task: retry all PENDENT and ERROR events."""
    from .models import Esdeveniment
    pendents = Esdeveniment.objects.filter(
        estat__in=[Esdeveniment.Estat.PENDENT, Esdeveniment.Estat.ERROR]
    ).values_list('pk', flat=True)

    for pk in pendents:
        sincronitzar_esdeveniment.delay(pk)
    logger.info('Reintentant sincronitzar %d esdeveniments', len(pendents))
