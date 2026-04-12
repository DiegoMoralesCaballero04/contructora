from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    """Registre d'auditoria per a totes les accions del sistema."""

    class Action(models.TextChoices):
        CREATE = 'CREATE', 'Creació'
        UPDATE = 'UPDATE', 'Actualització'
        DELETE = 'DELETE', 'Eliminació'
        LOGIN = 'LOGIN', 'Inici de sessió'
        LOGOUT = 'LOGOUT', 'Tancament de sessió'
        SCRAPING = 'SCRAPING', 'Scraping executat'
        EXTRACCION = 'EXTRACCION', 'Extracció IA'
        S3_UPLOAD = 'S3_UPLOAD', 'Pujada S3'
        S3_DOWNLOAD = 'S3_DOWNLOAD', 'Descàrrega S3'
        ALERT_SENT = 'ALERT_SENT', 'Alerta enviada'
        API_CALL = 'API_CALL', 'Crida API'

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    model_name = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=200, blank=True)
    object_repr = models.CharField(max_length=500, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Registre d\'auditoria'
        verbose_name_plural = 'Registres d\'auditoria'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['model_name', 'object_id']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'sistema'
        return f'{self.timestamp:%Y-%m-%d %H:%M} | {user_str} | {self.action} | {self.model_name}'
