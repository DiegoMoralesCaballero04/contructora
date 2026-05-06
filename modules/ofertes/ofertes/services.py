"""
Business logic for Ofertes module.
Separated from views/tasks to keep them thin.
"""
import logging
from decimal import Decimal
from typing import Optional

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Formula de puntuació econòmica ────────────────────────────────────────────

def calcular_preu_optim(
    pressupost_base: Decimal,
    formula: str,
    cost_empresa: Decimal,
    marge_minim: float = 0.05,
) -> dict:
    """
    Applies the scoring formula from the plec to find the optimal bid price.

    Supported formulas:
    - 'baixa_temeraria': classical Spanish public tender formula
      P_oferta = P_base × (1 - baixa)
      Puntuació = (baixa / baixa_max) × punts_max   (if baixa < baixa_temeraria)

    Returns:
        {
          'preu_optim': Decimal,
          'baixa_optima_pct': float,
          'puntuacio_estimada': float,
          'cost_cobert': bool,
        }
    """
    results = {}
    cost_minim = cost_empresa * Decimal(str(1 + marge_minim))

    if formula == 'baixa_temeraria':
        baixa_temeraria = Decimal('0.20')
        punt_max = Decimal('50')
        baixa_optima = baixa_temeraria * Decimal('0.95')
        preu = pressupost_base * (1 - baixa_optima)
        if preu < cost_minim:
            baixa_optima = 1 - (cost_minim / pressupost_base)
            preu = cost_minim
        puntuacio = float((baixa_optima / baixa_temeraria) * punt_max)
        results = {
            'preu_optim': preu.quantize(Decimal('0.01')),
            'baixa_optima_pct': float(baixa_optima * 100),
            'puntuacio_estimada': round(puntuacio, 2),
            'cost_cobert': preu >= cost_minim,
        }
    else:
        results = {
            'preu_optim': cost_minim.quantize(Decimal('0.01')),
            'baixa_optima_pct': 0.0,
            'puntuacio_estimada': 0.0,
            'cost_cobert': True,
        }

    return results


# ── Automatic Oferta creation from Licitacion ─────────────────────────────────

@transaction.atomic
def crear_oferta_des_de_licitacio(licitacio, user: Optional[User] = None):
    """
    Creates an Oferta for a licitacio that has moved to EN_PREPARACION.
    Idempotent: returns existing oferta if already created.
    """
    from .models import Oferta, Pressupost

    existing = getattr(licitacio, 'oferta', None)
    if existing:
        return existing, False

    oferta = Oferta.objects.create(
        licitacio=licitacio,
        estat=Oferta.Estat.BORRADOR,
        responsable=user,
    )
    Pressupost.objects.create(
        oferta=oferta,
        titol=f'Pressupost inicial — {licitacio.titol[:80]}',
        versio=1,
        actiu=True,
    )
    logger.info('Oferta %d creada per licitació %d', oferta.pk, licitacio.pk)
    return oferta, True


# ── Risk analysis ─────────────────────────────────────────────────────────────

def analitzar_risc(oferta) -> dict:
    """
    Heuristic risk scoring based on licitacion data and offer parameters.
    Returns risk level + list of risk factors.
    """
    factors = []
    score = 0

    licitacio = oferta.licitacio
    if licitacio.importe_base and licitacio.importe_base > 2_000_000:
        factors.append({'factor': 'import_elevat', 'gravetat': 'MITJA'})
        score += 1

    if licitacio.fecha_limite_oferta:
        dies = (licitacio.fecha_limite_oferta.date() - timezone.now().date()).days
        if dies < 14:
            factors.append({'factor': 'termini_curt', 'gravetat': 'ALT'})
            score += 2

    extraccion = getattr(licitacio, 'extraccion', None)
    if extraccion and extraccion.formula_economica:
        formula = extraccion.formula_economica.lower()
        if 'temeraria' not in formula and 'anormal' not in formula:
            factors.append({'factor': 'formula_desconeguda', 'gravetat': 'MITJA'})
            score += 1

    if oferta.preu_oferta and oferta.pressupost_cost_total:
        marge = float(oferta.preu_oferta) / float(oferta.pressupost_cost_total) - 1
        if marge < 0.03:
            factors.append({'factor': 'marge_baix', 'gravetat': 'ALT'})
            score += 2
        elif marge < 0.08:
            factors.append({'factor': 'marge_ajustat', 'gravetat': 'MITJA'})
            score += 1

    if score >= 3:
        nivell = 'ALT'
    elif score >= 1:
        nivell = 'MITJA'
    else:
        nivell = 'BAIX'

    return {'nivell_risc': nivell, 'factors_risc': factors, 'score': score}


# ── Document snapshot versioning ──────────────────────────────────────────────

def crear_versio_oferta(oferta, user: Optional[User] = None) -> 'VersioOferta':
    from .models import VersioOferta

    ultima = oferta.versions.first()
    numero = (ultima.numero_versio + 1) if ultima else 1

    snap = {
        'estat': oferta.estat,
        'preu_oferta': str(oferta.preu_oferta),
        'preu_optim_calculat': str(oferta.preu_optim_calculat),
        'puntuacio_total': str(oferta.puntuacio_total),
        'nivell_risc': oferta.nivell_risc,
        'factors_risc': oferta.factors_risc,
        'pressupostos': [
            {
                'id': p.id, 'titol': p.titol, 'versio': p.versio,
                'cost_total': str(p.cost_total),
                'linies': [
                    {
                        'descripcio': l.descripcio, 'tipus': l.tipus,
                        'quantitat': str(l.quantitat), 'cost_unitari': str(l.cost_unitari),
                    }
                    for l in p.linies.all()
                ],
            }
            for p in oferta.pressupostos.filter(actiu=True)
        ],
    }
    return VersioOferta.objects.create(
        oferta=oferta, numero_versio=numero, snap_data=snap, creada_per=user
    )
