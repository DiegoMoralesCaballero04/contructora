from django.apps import AppConfig


class LicitacionesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.licitaciones.licitaciones'
    label = 'licitaciones'
    verbose_name = 'Licitacions'

    def ready(self):
        import modules.licitaciones.licitaciones.signals  # noqa
