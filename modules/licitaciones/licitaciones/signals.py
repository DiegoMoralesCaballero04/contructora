from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Licitacion


@receiver(post_save, sender=Licitacion)
def on_licitacion_created(sender, instance, created, **kwargs):
    if created and instance.es_relevante:
        try:
            from modules.licitaciones.alertas.tasks import enviar_alerta_nova_licitacio
            enviar_alerta_nova_licitacio.delay(instance.pk)
        except ImportError:
            pass
