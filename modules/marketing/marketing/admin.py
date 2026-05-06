from django.contrib import admin
from django.utils.html import format_html
from .models import EmpresaProspect, CampanyaMarketing, PlantillaEmail, EnviamentEmail


@admin.register(EmpresaProspect)
class EmpresaProspectAdmin(admin.ModelAdmin):
    list_display = ('nom', 'sector', 'estat', 'scoring', 'email_principal', 'consentiment_gdpr', 'baixa_voluntaria')
    list_filter = ('sector', 'estat', 'consentiment_gdpr', 'baixa_voluntaria', 'provincia')
    search_fields = ('nom', 'email_principal', 'persona_contacte')
    readonly_fields = ('scoring', 'token_baixa', 'data_baixa', 'creada_en')
    ordering = ('-scoring',)


@admin.register(PlantillaEmail)
class PlantillaEmailAdmin(admin.ModelAdmin):
    list_display = ('nom', 'tipus', 'idioma', 'activa')
    list_filter = ('tipus', 'idioma', 'activa')


@admin.register(CampanyaMarketing)
class CampanyaMarketingAdmin(admin.ModelAdmin):
    list_display = (
        'nom', 'estat', 'plantilla', 'total_destinataris',
        'total_enviats', 'taxa_obertura', 'creada_en',
    )
    list_filter = ('estat',)
    readonly_fields = (
        'total_destinataris', 'total_enviats', 'total_errors',
        'total_obertures', 'total_clics', 'iniciada_en', 'completada_en',
    )

    def taxa_obertura(self, obj):
        return f'{obj.taxa_obertura}%'


@admin.register(EnviamentEmail)
class EnviamentEmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'prospect', 'campanya', 'estat', 'obert', 'enviat_en')
    list_filter = ('estat', 'obert')
    readonly_fields = ('tracking_token', 'enviat_en', 'obert_en', 'clicat_en')
