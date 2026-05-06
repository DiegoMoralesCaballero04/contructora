"""
Built-in search sources for the prospec module.
Registers all active sources via @registrar_font.
"""
from .sources_osm import font_osm_empreses  # noqa: F401 — registration side-effect

__all__ = ['font_osm_empreses']
