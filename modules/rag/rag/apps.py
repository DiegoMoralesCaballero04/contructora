from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RagConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.rag.rag'
    label = 'rag'
    verbose_name = _('Sistema RAG')
