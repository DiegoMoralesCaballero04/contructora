from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import ScrapingJob, ScrapingTemplate


@admin.register(ScrapingTemplate)
class ScrapingTemplateAdmin(admin.ModelAdmin):
    list_display = ('nom', 'activa', 'importe_min', 'importe_max', 'max_pagines')
    list_editable = ('activa',)
    fieldsets = (
        ('Configuración', {
            'fields': ('nom', 'activa', 'max_pagines')
        }),
        ('Filtros de Importe', {
            'fields': ('importe_min', 'importe_max'),
            'classes': ('collapse',)
        }),
        ('Territorio', {
            'fields': ('provincies',),
            'classes': ('collapse',)
        }),
        ('Tipos de Contrato', {
            'fields': ('tipus_contracte',),
            'classes': ('collapse',)
        }),
        ('Procedimientos', {
            'fields': ('procediments',),
            'classes': ('collapse',)
        }),
        ('CPV', {
            'fields': ('cpv_inclosos',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('creada_en', 'actualitzada_en'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('creada_en', 'actualitzada_en')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        template = ScrapingTemplate.objects.first()
        if template:
            return HttpResponseRedirect(reverse('admin:scraping_scrapingtemplate_change', args=[template.pk]))
        return super().changelist_view(request, extra_context)


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

