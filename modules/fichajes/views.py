"""
Fichajes module views.

This module groups all clock-in/attendance logic. It depends on the rrhh module
(Fichaje model lives in modules.rrhh.rrhh). If rrhh is absent, this module
has no effect.

Views here are registered into the portal namespace via apps/portal/urls.py.
"""
from modules.rrhh.rrhh.models import Fichaje, UserProfile
