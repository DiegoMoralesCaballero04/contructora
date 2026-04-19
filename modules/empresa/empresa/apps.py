from django.apps import AppConfig


class EmpresaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.empresa.empresa'
    label = 'empresa'
    verbose_name = 'Empresa'
