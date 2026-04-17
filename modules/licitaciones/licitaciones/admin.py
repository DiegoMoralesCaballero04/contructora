from django.contrib import admin
from django.utils.html import format_html
from .models import Licitacion, Organismo, CriterioAdjudicacion


class CriterioInline(admin.TabularInline):
    model = CriterioAdjudicacion
    extra = 0
    fields = ('nombre', 'puntuacion_maxima', 'es_economico', 'formula')


@admin.register(Licitacion)
class LicitacionAdmin(admin.ModelAdmin):
    list_display = (
        'expediente_id', 'titulo_corto', 'organismo', 'provincia',
        'importe_base', 'fecha_limite_oferta', 'dias_restantes_badge',
        'estado', 'pdf_badge', 'extraccion_badge',
    )
    list_filter = ('estado', 'provincia', 'procedimiento', 'pdf_descargado')
    search_fields = ('expediente_id', 'titulo', 'organismo__nombre')
    readonly_fields = ('expediente_id', 'url_origen', 'creado_en', 'actualizado_en', 'mongo_id')
    list_per_page = 25
    inlines = [CriterioInline]

    fieldsets = (
        ('Identificació', {
            'fields': ('expediente_id', 'url_origen', 'mongo_id'),
        }),
        ('Dades bàsiques', {
            'fields': ('titulo', 'organismo', 'provincia', 'municipio'),
        }),
        ('Econòmics', {
            'fields': ('importe_base', 'importe_iva'),
        }),
        ('Procediment i terminis', {
            'fields': ('procedimiento', 'fecha_publicacion', 'fecha_limite_oferta', 'plazo_ejecucion_dias'),
        }),
        ('Classificació empresarial', {
            'fields': ('clasificacion_grupo', 'clasificacion_subgrupo', 'clasificacion_categoria'),
        }),
        ('PDF', {
            'fields': ('pdf_pliego_s3_key', 'pdf_pliego_url', 'pdf_descargado'),
        }),
        ('Estat intern', {
            'fields': ('estado', 'es_relevante', 'notas'),
        }),
        ('Metadades', {
            'fields': ('creado_en', 'actualizado_en'),
        }),
    )

    def titulo_corto(self, obj):
        return obj.titulo[:70] + '...' if len(obj.titulo) > 70 else obj.titulo
    titulo_corto.short_description = 'Títol'

    def dias_restantes_badge(self, obj):
        days = obj.dias_restantes
        if days is None:
            return '—'
        color = 'red' if days < 7 else 'orange' if days < 14 else 'green'
        return format_html('<span style="color:{}">{} dies</span>', color, days)
    dias_restantes_badge.short_description = 'Dies restants'

    def pdf_badge(self, obj):
        if obj.pdf_descargado:
            return format_html('<span style="color:green">✓ S3</span>')
        return format_html('<span style="color:gray">—</span>')
    pdf_badge.short_description = 'PDF'

    def extraccion_badge(self, obj):
        if obj.tiene_extraccion:
            estado = obj.extraccion.estado
            color = 'green' if estado == 'OK' else 'red'
            return format_html('<span style="color:{}">{}</span>', color, estado)
        return format_html('<span style="color:gray">Pendent</span>')
    extraccion_badge.short_description = 'Extracció IA'


@admin.register(Organismo)
class OrganismoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nif', 'provincia', 'municipio')
    search_fields = ('nombre', 'nif')
    list_filter = ('provincia',)
