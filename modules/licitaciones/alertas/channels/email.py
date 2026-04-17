import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def enviar_email_nova_licitacio(destinatari: str, licitacio) -> bool:
    """Send a new tender alert email."""
    try:
        context = {
            'licitacio': licitacio,
            'url': f'http://localhost:8000/admin/licitaciones/licitacion/{licitacio.pk}/change/',
        }
        body_html = render_to_string('alertas/email_nova_licitacio.html', context)
        body_text = render_to_string('alertas/email_nova_licitacio.txt', context)

        send_mail(
            subject=f'[CONSTRUTECH-IA] Nova licitació: {licitacio.titulo[:80]}',
            message=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatari],
            html_message=body_html,
            fail_silently=False,
        )
        logger.info('Alert email sent to %s for licitacio %s', destinatari, licitacio.expediente_id)
        return True
    except Exception as e:
        logger.error('Failed to send email to %s: %s', destinatari, e)
        return False


def enviar_resum_diari(destinatari: str, licitacions: list, data) -> bool:
    """Send a daily digest email."""
    try:
        total_import = sum(
            float(l.importe_base or 0) for l in licitacions
        )
        subject = f'[CONSTRUTECH-IA] Resum diari {data} — {len(licitacions)} licitacions'
        body = f"""RESUM DIARI — {data}

Licitacions noves: {len(licitacions)}
Import total: {total_import:,.0f} EUR

"""
        for l in licitacions:
            body += f'• {l.titulo[:80]}\n'
            body += f'  Import: {l.importe_base:,.0f} EUR | Termini: {l.fecha_limite_oferta}\n\n'

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatari],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error('Failed to send daily digest: %s', e)
        return False
