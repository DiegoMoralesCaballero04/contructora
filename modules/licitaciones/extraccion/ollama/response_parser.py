"""
Parse and validate raw Ollama JSON responses for licitacion extraction.
LLMs sometimes wrap JSON in markdown or add extra text — this handles it.
"""
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ['objecte', 'pressupost_base', 'procediment']


def parse_extraction_response(raw_text: str) -> dict[str, Any]:
    """
    Parse the LLM response into a clean dict.
    Handles: pure JSON, JSON inside markdown blocks, JSON buried in text.
    Returns a dict with 'success', 'data', and 'error' keys.
    """
    if not raw_text or not raw_text.strip():
        return {'success': False, 'data': {}, 'error': 'Empty response'}

    # Attempt 1: parse directly
    try:
        data = json.loads(raw_text.strip())
        return {'success': True, 'data': _clean_data(data), 'error': None}
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract from markdown code block
    md_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', raw_text)
    if md_match:
        try:
            data = json.loads(md_match.group(1))
            return {'success': True, 'data': _clean_data(data), 'error': None}
        except json.JSONDecodeError:
            pass

    # Attempt 3: find first {...} block (greedy)
    brace_match = re.search(r'\{[\s\S]*\}', raw_text)
    if brace_match:
        try:
            data = json.loads(brace_match.group(0))
            return {'success': True, 'data': _clean_data(data), 'error': None}
        except json.JSONDecodeError:
            pass

    logger.warning('Could not parse LLM response as JSON. Raw (first 200): %s', raw_text[:200])
    return {
        'success': False,
        'data': {},
        'error': 'Could not parse JSON from LLM response',
        'raw': raw_text,
    }


def _clean_data(data: dict) -> dict:
    """Normalize extracted fields to expected types."""
    def to_decimal(v):
        if v is None:
            return None
        try:
            return float(str(v).replace(',', '.').replace('.', '', str(v).count('.') - 1))
        except (ValueError, TypeError):
            return None

    def to_int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    cleaned = {
        'objecte': str(data.get('objecte', '') or '').strip(),
        'pressupost_base': to_decimal(data.get('pressupost_base')),
        'pressupost_iva': to_decimal(data.get('pressupost_iva')),
        'termini_execucio_mesos': to_int(data.get('termini_execucio_mesos')),
        'termini_execucio_dies': to_int(data.get('termini_execucio_dies')),
        'data_limit_ofertes': str(data.get('data_limit_ofertes') or '').strip() or None,
        'procediment': str(data.get('procediment', 'OBERT')).upper(),
        'criteris_adjudicacio': data.get('criteris_adjudicacio', []),
        'formula_economica': str(data.get('formula_economica', '') or '').strip(),
        'classificacio_grup': str(data.get('classificacio_grup', '') or '').strip(),
        'classificacio_subgrup': str(data.get('classificacio_subgrup', '') or '').strip(),
        'classificacio_categoria': str(data.get('classificacio_categoria', '') or '').strip(),
        'requereix_declaracio_responsable': bool(data.get('requereix_declaracio_responsable', False)),
        'garantia_provisional': to_decimal(data.get('garantia_provisional')),
        'garantia_definitiva_percentatge': to_decimal(data.get('garantia_definitiva_percentatge')),
    }

    # Clean criteris array
    criteris = []
    for c in cleaned['criteris_adjudicacio']:
        if isinstance(c, dict):
            criteris.append({
                'nom': str(c.get('nom', '')),
                'puntuacio': to_decimal(c.get('puntuacio')) or 0,
                'formula': str(c.get('formula', '') or ''),
                'es_economic': bool(c.get('es_economic', False)),
            })
    cleaned['criteris_adjudicacio'] = criteris

    return cleaned
