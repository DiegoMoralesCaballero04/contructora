from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CalendariConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.calendari.calendari'
    label = 'calendari'
    verbose_name = _('Calendari Laboral')
