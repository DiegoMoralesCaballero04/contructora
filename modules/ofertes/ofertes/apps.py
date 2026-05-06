from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OfertesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.ofertes.ofertes'
    label = 'ofertes'
    verbose_name = _('Ofertes i Pressupostos')
