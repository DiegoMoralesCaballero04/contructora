import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def enviar_enviament(self, enviament_pk: int):
    """Send a single marketing email. Respects GDPR and bounce logic."""
    try:
        from .models import EnviamentEmail
        from django.core.mail import EmailMultiAlternatives

        enviament = EnviamentEmail.objects.select_related(
            'prospect', 'campanya__plantilla'
        ).get(pk=enviament_pk)

        if not enviament.prospect.pot_rebre_emails:
            enviament.estat = EnviamentEmail.Estat.REBUTJAT
            enviament.error_msg = 'GDPR: prospect no pot rebre emails'
            enviament.save(update_fields=['estat', 'error_msg'])
            return

        enviament.estat = EnviamentEmail.Estat.ENVIANT
        enviament.save(update_fields=['estat'])

        unsubscribe_url = _build_unsubscribe_url(enviament.prospect)

        text = enviament.cos_final_text + f'\n\n---\nCancellar subscripció: {unsubscribe_url}'
        html = enviament.cos_final_html or ''
        if html:
            html += f'<p><small><a href="{unsubscribe_url}">Donar-se de baixa</a></small></p>'
            tracking_pixel = f'<img src="{_build_tracking_pixel_url(enviament)}" width="1" height="1" />'
            html += tracking_pixel

        msg = EmailMultiAlternatives(
            subject=enviament.assumpte_final,
            body=text,
            to=[enviament.prospect.email_principal],
        )
        if html:
            msg.attach_alternative(html, 'text/html')
        msg.send()

        enviament.estat = EnviamentEmail.Estat.ENVIAT
        enviament.enviat_en = timezone.now()
        enviament.save(update_fields=['estat', 'enviat_en'])

        from .models import CampanyaMarketing
        CampanyaMarketing.objects.filter(pk=enviament.campanya_id).update(
            total_enviats=models_F('total_enviats') + 1
        )

    except Exception as exc:
        logger.error('Error enviant email %d: %s', enviament_pk, exc)
        from .models import EnviamentEmail
        EnviamentEmail.objects.filter(pk=enviament_pk).update(
            estat=EnviamentEmail.Estat.ERROR,
            error_msg=str(exc),
        )
        raise self.retry(exc=exc, countdown=120)


@shared_task
def executar_campanya(campanya_pk: int):
    """
    Main campaign executor:
    1. Segments prospects
    2. Optionally improves email with AI
    3. Creates EnviamentEmail records
    4. Chains individual send tasks
    """
    try:
        from .models import CampanyaMarketing, EnviamentEmail
        from .services import segmentar_prospects, millorar_email_amb_ia

        campanya = CampanyaMarketing.objects.select_related('plantilla').get(pk=campanya_pk)
        campanya.estat = CampanyaMarketing.Estat.EN_CURS
        campanya.iniciada_en = timezone.now()
        campanya.save(update_fields=['estat', 'iniciada_en'])

        prospects = segmentar_prospects(campanya.segments)
        campanya.total_destinataris = prospects.count()
        campanya.save(update_fields=['total_destinataris'])

        enviaments_pk = []
        for prospect in prospects.iterator():
            if EnviamentEmail.objects.filter(campanya=campanya, prospect=prospect).exists():
                continue

            assumpte = campanya.plantilla.assumpte
            cos_text = campanya.plantilla.cos_text
            cos_html = campanya.plantilla.cos_html

            if campanya.millorar_amb_ia and campanya.personalitzar_per_empresa:
                text_millorat = millorar_email_amb_ia(cos_text, prospect)
                if text_millorat:
                    cos_text = text_millorat

            env = EnviamentEmail.objects.create(
                campanya=campanya,
                prospect=prospect,
                assumpte_final=assumpte,
                cos_final_text=cos_text,
                cos_final_html=cos_html,
            )
            enviaments_pk.append(env.pk)

        for pk in enviaments_pk:
            enviar_enviament.apply_async(args=[pk], countdown=1)

        campanya.estat = CampanyaMarketing.Estat.COMPLETADA
        campanya.completada_en = timezone.now()
        campanya.save(update_fields=['estat', 'completada_en'])

        logger.info('Campanya %d completada: %d enviaments', campanya_pk, len(enviaments_pk))

    except Exception as exc:
        logger.error('Error executant campanya %d: %s', campanya_pk, exc)
        from .models import CampanyaMarketing
        CampanyaMarketing.objects.filter(pk=campanya_pk).update(estat=CampanyaMarketing.Estat.PAUSADA)
        raise


@shared_task
def actualitzar_scoring_prospects():
    """Daily task: recalculate scoring for all prospects."""
    from .services import actualitzar_scoring_all
    actualitzar_scoring_all()


@shared_task
def importar_prospects_licitacions():
    """Weekly task: auto-import new prospects from licitacion organismos."""
    from .services import importar_prospects_des_de_licitacions
    importar_prospects_des_de_licitacions()


def _build_unsubscribe_url(prospect) -> str:
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', 'http://localhost')
    return f'{base}/marketing/baixa/{prospect.token_baixa}/'


def _build_tracking_pixel_url(enviament) -> str:
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', 'http://localhost')
    return f'{base}/marketing/track/{enviament.tracking_token}/open.gif'


def models_F(field):
    from django.db.models import F
    return F(field)
