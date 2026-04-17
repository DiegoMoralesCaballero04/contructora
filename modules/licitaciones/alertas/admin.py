from django.contrib import admin
from .models import AlertaConfig


@admin.register(AlertaConfig)
class AlertaConfigAdmin(admin.ModelAdmin):
    list_display = ('usuari', 'activa', 'email_actiu', 'telegram_actiu', 'importe_max')
    list_filter = ('activa', 'email_actiu', 'telegram_actiu')
