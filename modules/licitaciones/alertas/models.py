from django.db import models
from django.contrib.auth.models import User


class AlertaConfig(models.Model):
    """Per-user configuration for new tender alerts."""
    usuari = models.OneToOneField(User, on_delete=models.CASCADE, related_name='alerta_config')

    activa = models.BooleanField(default=True)
    email_actiu = models.BooleanField(default=True)
    telegram_actiu = models.BooleanField(default=False)

    # Filters
    importe_max = models.DecimalField(max_digits=14, decimal_places=2, default=4_000_000)
    provincies = models.JSONField(default=list, help_text='Llista de províncies. Buit = totes.')
    procediments = models.JSONField(default=list, help_text='Llista de procediments. Buit = tots.')

    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Configuració d'alerta"
        verbose_name_plural = "Configuracions d'alerta"

    def __str__(self):
        return f'AlertaConfig de {self.usuari.username}'
