"""
Prospecció intel·ligent — registry of search sources.

Each source is a callable that receives (ubicacio, sector, paraules_clau, limit)
and returns a list of dicts with keys:
  nom, sector, poblacio, provincia, email, web, telefon, notes,
  de_licitacio, licitacio_pk, licitacio_titol, licitacio_expediente,
  licitacio_import, licitacio_termini, import_referencia, font
"""

_SOURCES = []


def registrar_font(fn):
    _SOURCES.append(fn)
    return fn


def cercar_tots(ubicacio, sector, paraules_clau, limit=60):
    resultats = []
    vists = set()
    per_font = max(limit // max(len(_SOURCES), 1), 10)

    for font_fn in _SOURCES:
        try:
            parcials = font_fn(ubicacio, sector, paraules_clau, per_font)
            for r in parcials:
                key = r.get('nom', '').strip().lower()
                if key and key not in vists:
                    vists.add(key)
                    resultats.append(r)
        except Exception:
            pass

    return resultats[:limit]
