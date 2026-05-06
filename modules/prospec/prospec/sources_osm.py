"""
OpenStreetMap source for external company prospecting.
Uses Nominatim for geocoding and Overpass API for business search.
No API keys required.
"""
import json
import logging

import httpx

from .registry import registrar_font

logger = logging.getLogger(__name__)

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
OVERPASS_URL = 'https://overpass.kumi.systems/api/interpreter'
HEADERS = {'User-Agent': 'ConstruTech-IA/1.0 (contact@construtech.es)'}

SECTOR_TAGS = {
    'CONSTRUCCIO': [
        ('office', 'construction'), ('craft', 'construction'),
        ('office', 'architect'), ('craft', 'carpenter'),
        ('craft', 'electrician'), ('craft', 'plumber'),
        ('craft', 'roofer'), ('craft', 'painter'),
        ('craft', 'metal_construction'), ('craft', 'glaziery'),
        ('office', 'engineer'),
    ],
    'ENGINYERIA': [
        ('office', 'engineer'), ('office', 'technical'),
        ('office', 'consulting'), ('office', 'industrial_designer'),
        ('office', 'it'),
    ],
    'PROMOTORA': [
        ('office', 'estate_agent'), ('office', 'real_estate'),
        ('office', 'property_management'),
    ],
    'ADMINISTRACIO': [
        ('office', 'government'), ('amenity', 'townhall'),
        ('office', 'administrative'), ('office', 'public_administration'),
    ],
}

ALL_TAGS = [
    ('office', None), ('craft', None),
]


def geocodificar(query: str):
    try:
        resp = httpx.get(
            NOMINATIM_URL,
            params={'q': query, 'format': 'json', 'limit': 1, 'countrycodes': 'es'},
            headers=HEADERS,
            timeout=6,
        )
        data = resp.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        logger.warning('Nominatim error per "%s": %s', query, e)
    return None


def _construir_query(lat, lon, radius_m, sector, fetch_limit):
    tags = SECTOR_TAGS.get(sector) if sector else None

    parts = ['[out:json][timeout:10];', '(']
    if tags:
        for key, val in tags:
            parts.append(f'  node["{key}"="{val}"](around:{radius_m},{lat},{lon});')
            parts.append(f'  way["{key}"="{val}"](around:{radius_m},{lat},{lon});')
    else:
        parts.append(f'  node["office"](around:{radius_m},{lat},{lon});')
        parts.append(f'  node["craft"](around:{radius_m},{lat},{lon});')
        parts.append(f'  way["office"](around:{radius_m},{lat},{lon});')
        parts.append(f'  way["craft"](around:{radius_m},{lat},{lon});')

    parts.append(');')
    parts.append(f'out center {fetch_limit};')
    return '\n'.join(parts)


def _sector_from_tags(tags):
    office = tags.get('office', '')
    craft = tags.get('craft', '')
    if office in ('construction', 'architect', 'engineer') or craft in (
        'construction', 'roofer', 'electrician', 'plumber',
        'carpenter', 'painter', 'metal_construction', 'glaziery',
    ):
        return 'CONSTRUCCIO'
    if office in ('engineer', 'technical', 'consulting', 'industrial_designer', 'it'):
        return 'ENGINYERIA'
    if office in ('estate_agent', 'real_estate', 'property_management'):
        return 'PROMOTORA'
    if office in ('government', 'administrative', 'public_administration'):
        return 'ADMINISTRACIO'
    return 'ALTRES'


@registrar_font
def font_osm_empreses(ubicacio, sector, paraules_clau, limit):
    """Searches real businesses near a location using OpenStreetMap."""
    if not ubicacio:
        return []

    coords = geocodificar(ubicacio)
    if not coords:
        logger.warning('No s\'ha pogut geocodificar: %s', ubicacio)
        return []

    lat, lon = coords
    radius_m = 10000
    query = _construir_query(lat, lon, radius_m, sector, limit * 2)

    try:
        resp = httpx.post(OVERPASS_URL, data={'data': query}, timeout=15)
        elements = json.loads(resp.content).get('elements', [])
    except Exception as e:
        logger.error('Overpass API error: %s', e)
        return []

    resultats = []
    vists = set()
    kw = paraules_clau.lower() if paraules_clau else ''

    for el in elements:
        tags = el.get('tags', {})
        nom = tags.get('name', '').strip()
        if not nom or nom.lower() in vists:
            continue

        if kw and kw not in nom.lower() and kw not in tags.get('description', '').lower():
            continue

        vists.add(nom.lower())

        el_lat = el.get('lat') or el.get('center', {}).get('lat', lat)
        el_lon = el.get('lon') or el.get('center', {}).get('lon', lon)

        email = tags.get('email') or tags.get('contact:email', '')
        web = tags.get('website') or tags.get('contact:website') or tags.get('url', '')
        tel = tags.get('phone') or tags.get('contact:phone', '')
        city = (tags.get('addr:city') or tags.get('addr:town') or
                tags.get('addr:village') or ubicacio)
        street = ''
        if tags.get('addr:street'):
            street = f"{tags['addr:street']} {tags.get('addr:housenumber', '')}".strip()

        sector_det = _sector_from_tags(tags)
        tipus = tags.get('office', tags.get('craft', tags.get('amenity', '')))

        resultats.append({
            'nom': nom,
            'sector': sector_det if not sector else sector,
            'poblacio': city,
            'provincia': '',
            'email': email,
            'web': web,
            'telefon': tel,
            'adreça': street,
            'notes': f'Font: OpenStreetMap. Tipus: {tipus}. OSM#{el["id"]}',
            'de_licitacio': False,
            'licitacio_pk': None,
            'licitacio_titol': '',
            'licitacio_expediente': '',
            'licitacio_import': 0,
            'licitacio_termini': '',
            'import_referencia': 0,
            'font': 'OpenStreetMap',
            'osm_tipus': tipus,
            'lat': el_lat,
            'lon': el_lon,
        })

        if len(resultats) >= limit:
            break

    return resultats
