from django.contrib import admin
from django.utils.html import format_html
from .models import Oferta, VersioOferta, Pressupost, LiniaPressupost, SolicitudSubcontractista, PlaSeguretat


class LiniaPressupostInline(admin.TabularInline):
    model = LiniaPressupost
    extra = 0
    fields = ('tipus', 'descripcio', 'unitat', 'quantitat', 'cost_unitari', 'ordre')


class PressupostInline(admin.StackedInline):
    model = Pressupost
    extra = 0
    fields = ('titol', 'versio', 'actiu', 'cost_total', 'notes')
    readonly_fields = ('cost_total',)
    show_change_link = True


class SolicitudInline(admin.TabularInline):
    model = SolicitudSubcontractista
    extra = 0
    fields = ('contacte', 'estat', 'preu_resposta', 'enviada_en')
    readonly_fields = ('enviada_en',)


@admin.register(Oferta)
class OfertaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'licitacio_titol', 'estat_badge', 'preu_oferta',
        'preu_optim_calculat', 'risc_badge', 'responsable', 'creada_en',
    )
    list_filter = ('estat', 'nivell_risc')
    search_fields = ('licitacio__titol', 'licitacio__expediente_id')
    readonly_fields = (
        'preu_optim_calculat', 'puntuacio_economica', 'puntuacio_total',
        'factors_risc', 'creada_en', 'actualitzada_en',
    )
    inlines = [PressupostInline, SolicitudInline]

    def licitacio_titol(self, obj):
        return obj.licitacio.titol[:60]

    def estat_badge(self, obj):
        colors = {
            'BORRADOR': '#888', 'EN_REVISIO': '#f0ad4e', 'APROVADA': '#5bc0de',
            'ENVIADA': '#428bca', 'GUANYADA': '#5cb85c', 'PERDUDA': '#d9534f',
        }
        color = colors.get(obj.estat, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px">{}</span>',
            color, obj.get_estat_display()
        )
    estat_badge.short_description = 'Estat'

    def risc_badge(self, obj):
        colors = {'BAIX': '#5cb85c', 'MITJA': '#f0ad4e', 'ALT': '#d9534f'}
        color = colors.get(obj.nivell_risc, '#888')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 6px;border-radius:4px">{}</span>',
            color, obj.nivell_risc
        )
    risc_badge.short_description = 'Risc'


@admin.register(Pressupost)
class PressupostAdmin(admin.ModelAdmin):
    list_display = ('id', 'oferta', 'titol', 'versio', 'actiu', 'cost_total')
    inlines = [LiniaPressupostInline]


@admin.register(PlaSeguretat)
class PlaSeguretatAdmin(admin.ModelAdmin):
    list_display = ('id', 'oferta', 'validat', 'validat_per', 'generat_en')
    readonly_fields = ('contingut_ia', 'model_usat', 'prompt_versio', 'generat_en')
