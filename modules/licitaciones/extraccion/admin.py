import json
from django.contrib import admin
from django.utils.html import format_html
from .models import Extraccion


@admin.register(Extraccion)
class ExtraccionAdmin(admin.ModelAdmin):
    list_display = (
        'licitacio', 'estat_badge', 'pressupost_extret', 'termini_mesos',
        'model_usat', 'intents', 'actualitzada_en',
    )
    list_filter = ('estat', 'model_usat', 'prompt_versio')
    readonly_fields = (
        'licitacio', 'estat', 'model_usat', 'prompt_versio',
        'intents', 'creada_en', 'actualitzada_en', 'mongo_extraccion_id',
    )
    search_fields = ('licitacio__expediente_id', 'licitacio__titulo')

    fieldsets = (
        ('Licitació', {'fields': ('licitacio',)}),
        ('Estat', {'fields': ('estat', 'intents', 'error_msg', 'model_usat', 'prompt_versio')}),
        ('Dades extretes', {
            'fields': (
                'objecte_extret', 'pressupost_extret', 'termini_mesos',
                'data_limit', 'formula_economica', 'classificacio_completa',
                'requereix_declaracio',
            ),
        }),
        ('Resum IA', {'fields': ('resum_executiu',)}),
        ('Metadades', {
            'fields': ('creada_en', 'actualitzada_en', 'mongo_extraccion_id'),
        }),
    )

    def estat_badge(self, obj):
        colors = {
            'PENDENT': 'gray', 'EN_CURS': 'blue',
            'OK': 'green', 'ERROR': 'red', 'REVISAR': 'orange',
        }
        color = colors.get(obj.estat, 'gray')
        return format_html('<span style="color:{}">{}</span>', color, obj.estat)
    estat_badge.short_description = 'Estat'

    actions = ['retry_extraction']

    def retry_extraction(self, request, queryset):
        from modules.licitaciones.extraccion.tasks import extreure_dades_pdf
        count = 0
        for extraccion in queryset:
            extreure_dades_pdf.delay(extraccion.licitacio_id)
            count += 1
        self.message_user(request, f'{count} extraccions reintentades.')
    retry_extraction.short_description = 'Reintentar extracció'
