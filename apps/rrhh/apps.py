from django.apps import AppConfig


class RrhhConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.rrhh'
    verbose_name = 'Recursos Humans'

    def ready(self):
        import apps.rrhh.signals  # noqa: F401
