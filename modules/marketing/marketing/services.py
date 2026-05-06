"""
Marketing services: prospect scoring, segmentation, AI email improvement.
"""
import logging
from typing import Optional

from django.db.models import QuerySet

logger = logging.getLogger(__name__)

EMAIL_IMPROVEMENT_PROMPT = """Ets un expert en comunicació comercial B2B del sector de la construcció.

Tens una plantilla d'email per enviar a una empresa i informació sobre ella.
Millora l'email personalitzant-lo per a l'empresa destinatària.

PLANTILLA ORIGINAL:
---
{plantilla_text}
---

INFORMACIÓ DE L'EMPRESA DESTINATÀRIA:
- Nom: {nom_empresa}
- Sector: {sector}
- Provincia: {provincia}
- Persona de contacte: {contacte}

INSTRUCCIONS:
- Mantén el to professional i cordial
- Personalitza la introducció referint-te a l'empresa per nom
- Adapta el cos per al sector específic si és rellevant
- Mantén el missatge curt (màxim 4 paràgrafs)
- Usa el mateix idioma que la plantilla original
- NO inventis dades que no tens
- Torna NOMÉS el text de l'email millorat, sense explicacions ni notes"""


def calcular_scoring_prospect(prospect) -> float:
    """
    Heuristic score 0-10 for prospect potential.
    Base score for existing, bonus for completeness and engagement.
    """
    score = 1.0

    if prospect.email_principal:
        score += 2.0
    if prospect.consentiment_gdpr:
        score += 1.5
    if prospect.persona_contacte:
        score += 1.0
    if prospect.telefon:
        score += 0.5
    if prospect.web:
        score += 0.5
    if prospect.provincia or prospect.poblacio:
        score += 0.5
    if prospect.sector in ('CONSTRUCCIO', 'ENGINYERIA', 'PROMOTORA'):
        score += 1.5
    elif prospect.sector == 'ADMINISTRACIO':
        score += 0.5
    if prospect.estat == 'CLIENT':
        score += 2.0
    elif prospect.estat == 'INTERESSAT':
        score += 1.0
    elif prospect.estat == 'CONTACTAT':
        score += 0.5
    if prospect.origen == 'LICITACIO':
        score += 0.5

    return min(round(score, 1), 10.0)


def actualitzar_scoring_all():
    """Bulk-update scoring for all prospects."""
    from .models import EmpresaProspect
    for prospect in EmpresaProspect.objects.all():
        nou_score = calcular_scoring_prospect(prospect)
        if abs(prospect.scoring - nou_score) > 0.01:
            prospect.scoring = nou_score
            prospect.save(update_fields=['scoring', 'actualitzada_en'])


def segmentar_prospects(segments: dict) -> QuerySet:
    """
    Filter prospects by segment dict.
    Keys: sector, provincia, scoring_min, scoring_max, estat
    """
    from .models import EmpresaProspect
    qs = EmpresaProspect.objects.filter(
        baixa_voluntaria=False,
        consentiment_gdpr=True,
    ).exclude(email_principal='')

    if sectors := segments.get('sector'):
        qs = qs.filter(sector__in=sectors)
    if provincies := segments.get('provincia'):
        qs = qs.filter(provincia__in=provincies)
    if scoring_min := segments.get('scoring_min'):
        qs = qs.filter(scoring__gte=scoring_min)
    if scoring_max := segments.get('scoring_max'):
        qs = qs.filter(scoring__lte=scoring_max)
    if estats := segments.get('estat'):
        qs = qs.filter(estat__in=estats)

    return qs


def millorar_email_amb_ia(plantilla_text: str, prospect) -> Optional[str]:
    """
    Use local Ollama LLM to personalize email template for a specific company.
    Returns improved text or None if LLM unavailable.
    """
    try:
        from django.conf import settings
        from modules.licitaciones.extraccion.ollama.client import OllamaClient

        client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        if not client.is_available():
            logger.warning('Ollama no disponible, usant plantilla original')
            return None

        prompt = EMAIL_IMPROVEMENT_PROMPT.format(
            plantilla_text=plantilla_text,
            nom_empresa=prospect.nom,
            sector=prospect.get_sector_display(),
            provincia=prospect.provincia or 'no especificada',
            contacte=prospect.persona_contacte or 'no especificat',
        )
        return client.generate(prompt)

    except Exception as e:
        logger.error('Error millorant email amb IA: %s', e)
        return None


def importar_prospects_des_de_licitacions():
    """
    Auto-discover potential prospects from existing licitacion organismos.
    Only creates records for organismos not already in the prospect DB.
    """
    from modules.licitaciones.licitaciones.models import Licitacion
    from .models import EmpresaProspect

    licitacions = Licitacion.objects.select_related('organismo').filter(
        organismo__isnull=False
    ).values(
        'organismo__nombre', 'organismo__provincia', 'provincia', 'id'
    ).distinct()[:500]

    created = 0
    seen_noms = set()
    for row in licitacions:
        nom = row.get('organismo__nombre', '') or ''
        nom = nom.strip()
        if not nom or nom in seen_noms:
            continue
        seen_noms.add(nom)
        if EmpresaProspect.objects.filter(nom__iexact=nom).exists():
            continue
        EmpresaProspect.objects.create(
            nom=nom,
            email_principal='',
            provincia=row.get('organismo__provincia') or row.get('provincia', ''),
            origen=EmpresaProspect.Origen.LICITACIO,
            sector=EmpresaProspect.Sector.ADMINISTRACIO,
            consentiment_gdpr=False,
        )
        created += 1

    logger.info('Importats %d prospects des de licitacions', created)
    return created
