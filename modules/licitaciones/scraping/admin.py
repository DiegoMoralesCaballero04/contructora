from django.contrib import admin
from django.utils.html import format_html
from .models import ScrapingJob, ScrapingTemplate


@admin.register(ScrapingTemplate)
class ScrapingTemplateAdmin(admin.ModelAdmin):
    list_display = ('nom', 'activa', 'importe_min', 'importe_max', 'max_pagines', 'creada_en')
    list_filter = ('activa',)
    list_editable = ('activa',)


@admin.register(ScrapingJob)
class ScrapingJobAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'template', 'estat_badge', 'iniciat_en', 'duracio_display',
        'total_trobades', 'noves_insertades', 'errors',
    )
    list_filter = ('estat', 'template')
    readonly_fields = (
        'template', 'iniciat_en', 'finalitzat_en', 'estat',
        'total_trobades', 'noves_insertades', 'actualitzades',
        'descartades', 'errors', 'detalls_error', 'filtres_aplicats',
    )

    def estat_badge(self, obj):
        colors = {
            'PENDENT': 'gray', 'EN_CURS': 'blue',
            'COMPLETAT': 'green', 'ERROR': 'red',
        }
        color = colors.get(obj.estat, 'gray')
        return format_html('<span style="color:{}">{}</span>', color, obj.estat)
    estat_badge.short_description = 'Estat'

    def duracio_display(self, obj):
        secs = obj.duracio_segons
        if secs is None:
            return '—'
        return f'{secs:.0f}s'
    duracio_display.short_description = 'Duració'

    def has_add_permission(self, request):
        return False
