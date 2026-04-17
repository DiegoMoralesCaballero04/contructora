from django.apps import AppConfig


class RrhhConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.rrhh.rrhh'
    label = 'rrhh'
    verbose_name = 'Recursos Humans'

    def ready(self):
        import modules.rrhh.rrhh.signals  # noqa: F401
