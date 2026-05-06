import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

PSS_PROMPT_V1 = """Ets un tècnic expert en prevenció de riscos laborals a Espanya.
A partir de les partides d'obra que se't proporcionen, genera un ESBORRANY del Pla de Seguretat i Salut.

Partides d'obra:
{partides}

Genera el document amb les seccions:
1. Objecte i àmbit d'aplicació
2. Identificació de riscos per partida
3. Mesures preventives específiques
4. EPI necessaris
5. Procediments d'emergència bàsics

IMPORTANT: Aquest document és un ESBORRANY que ha de ser revisat per un tècnic qualificat.
Format: text professional en català."""


@shared_task(bind=True, max_retries=3)
def generar_pla_seguretat_ia(self, oferta_pk: int):
    """Generate PSS draft using local Ollama LLM."""
    try:
        from .models import Oferta, PlaSeguretat
        from modules.licitaciones.extraccion.ollama.client import OllamaClient

        oferta = Oferta.objects.select_related('licitacio').get(pk=oferta_pk)
        pss, _ = PlaSeguretat.objects.get_or_create(
            oferta=oferta,
            defaults={'partides_obra': []},
        )

        extraccion = getattr(oferta.licitacio, 'extraccion', None)
        partides = []
        if extraccion and extraccion.objecte:
            partides = [extraccion.objecte]
        if not partides:
            partides = ['Obra civil general']

        pss.partides_obra = partides
        pss.save(update_fields=['partides_obra'])

        client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        prompt = PSS_PROMPT_V1.format(partides='\n'.join(f'- {p}' for p in partides))
        resp = client.generate(prompt)

        pss.contingut_ia = resp
        pss.model_usat = settings.OLLAMA_MODEL
        pss.prompt_versio = 'v1'
        pss.save(update_fields=['contingut_ia', 'model_usat', 'prompt_versio', 'actualitzat_en'])
        logger.info('PSS generat per oferta %d', oferta_pk)

    except Exception as exc:
        logger.error('Error generant PSS per oferta %d: %s', oferta_pk, exc)
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def enviar_solicituds_subcontractistes(self, oferta_pk: int):
    """Send quote requests to subcontractors for an offer."""
    try:
        from .models import Oferta, SolicitudSubcontractista
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string

        oferta = Oferta.objects.select_related(
            'licitacio', 'licitacio__organismo'
        ).get(pk=oferta_pk)

        solicituds = SolicitudSubcontractista.objects.filter(
            oferta=oferta,
            estat=SolicitudSubcontractista.Estat.PENDENT,
        ).select_related('contacte')

        for sol in solicituds:
            if not sol.contacte.email:
                continue
            context = {
                'oferta': oferta,
                'licitacio': oferta.licitacio,
                'sol': sol,
                'partides': sol.partides,
            }
            text = render_to_string('ofertes/email_solicitud_subcontractista.txt', context)
            html = render_to_string('ofertes/email_solicitud_subcontractista.html', context)
            msg = EmailMultiAlternatives(
                subject=f'Sol·licitud de pressupost — {oferta.licitacio.titol[:60]}',
                body=text,
                to=[sol.contacte.email],
            )
            msg.attach_alternative(html, 'text/html')
            msg.send()

            sol.estat = SolicitudSubcontractista.Estat.ENVIADA
            sol.save(update_fields=['estat', 'enviada_en'])
            from django.utils import timezone
            sol.enviada_en = timezone.now()
            sol.save(update_fields=['enviada_en'])

        logger.info('Solicituds enviades per oferta %d: %d', oferta_pk, solicituds.count())

    except Exception as exc:
        logger.error('Error enviant solicituds per oferta %d: %s', oferta_pk, exc)
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True, max_retries=2)
def calcular_preu_optim_task(self, oferta_pk: int):
    """Recalculate optimal price for an offer and persist results."""
    try:
        from decimal import Decimal
        from .models import Oferta
        from .services import calcular_preu_optim, analitzar_risc

        oferta = Oferta.objects.select_related('licitacio__extraccion').get(pk=oferta_pk)
        licitacio = oferta.licitacio

        pressupost_base = licitacio.importe_base or Decimal('0')
        cost_empresa = oferta.pressupost_cost_total or Decimal('0')

        formula = 'baixa_temeraria'
        extraccion = getattr(licitacio, 'extraccion', None)
        if extraccion and extraccion.formula_economica:
            formula_text = extraccion.formula_economica.lower()
            if 'proporcional' in formula_text:
                formula = 'proporcional'

        if pressupost_base > 0 and cost_empresa > 0:
            resultat = calcular_preu_optim(pressupost_base, formula, cost_empresa)
            oferta.preu_optim_calculat = resultat['preu_optim']
            oferta.puntuacio_economica = Decimal(str(resultat['puntuacio_estimada']))
            oferta.save(update_fields=['preu_optim_calculat', 'puntuacio_economica', 'actualitzada_en'])

        risc = analitzar_risc(oferta)
        oferta.nivell_risc = risc['nivell_risc']
        oferta.factors_risc = risc['factors_risc']
        oferta.save(update_fields=['nivell_risc', 'factors_risc', 'actualitzada_en'])

        logger.info('Preu òptim calculat per oferta %d: %s', oferta_pk, oferta.preu_optim_calculat)

    except Exception as exc:
        logger.error('Error calculant preu òptim per oferta %d: %s', oferta_pk, exc)
        raise self.retry(exc=exc, countdown=30)


@shared_task
def auto_crear_oferta_per_en_preparacio(licitacio_pk: int):
    """
    Triggered when a Licitacion transitions to EN_PREPARACION.
    Auto-creates an Oferta and kicks off price calculation.
    """
    try:
        from modules.licitaciones.licitaciones.models import Licitacion
        from .services import crear_oferta_des_de_licitacio

        licitacio = Licitacion.objects.get(pk=licitacio_pk)
        oferta, created = crear_oferta_des_de_licitacio(licitacio)
        if created:
            generar_pla_seguretat_ia.delay(oferta.pk)
            logger.info('Oferta %d auto-creada per licitació %d', oferta.pk, licitacio_pk)
    except Exception as exc:
        logger.error('Error auto-creant oferta per licitació %d: %s', licitacio_pk, exc)
