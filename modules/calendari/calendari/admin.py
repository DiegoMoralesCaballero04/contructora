from django.contrib import admin
from .models import Esdeveniment, CalendariConfig


@admin.register(Esdeveniment)
class EsdevenimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipus', 'titol', 'inici', 'fi', 'estat', 'creador')
    list_filter = ('tipus', 'estat')
    search_fields = ('titol', 'descripcio')
    date_hierarchy = 'inici'
    readonly_fields = ('ms_event_id', 'estat', 'error_msg', 'creada_en', 'actualitzada_en')
    filter_horizontal = ('assistents',)


@admin.register(CalendariConfig)
class CalendariConfigAdmin(admin.ModelAdmin):
    list_display = ('usuari', 'esta_connectat', 'sincronitzar_licitacions', 'dies_avis_previ')
    readonly_fields = ('ms_access_token', 'ms_refresh_token', 'ms_token_expiry', 'esta_connectat')
