from django.contrib import admin
from .models import Client, Pedido, LiniaPedido, Albara, LiniaAlbara, Factura, LiniaFactura


class LiniaPedidoInline(admin.TabularInline):
    model = LiniaPedido
    extra = 1


class LiniaAlbaraInline(admin.TabularInline):
    model = LiniaAlbara
    extra = 1


class LiniaFacturaInline(admin.TabularInline):
    model = LiniaFactura
    extra = 1


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'nif', 'email', 'telefon', 'poblacio', 'actiu']
    search_fields = ['nom', 'nif', 'email']
    list_filter = ['actiu', 'pais']


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'client', 'estat', 'data', 'data_entrega']
    list_filter = ['estat']
    search_fields = ['numero', 'client__nom']
    inlines = [LiniaPedidoInline]


@admin.register(Albara)
class AlbaraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'client', 'estat', 'data']
    list_filter = ['estat']
    search_fields = ['numero', 'client__nom']
    inlines = [LiniaAlbaraInline]


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['numero_complet', 'client', 'estat', 'data_emisio', 'base_imponible', 'total_iva', 'total', 'verifactu']
    list_filter = ['estat', 'tipus', 'verifactu', 'serie']
    search_fields = ['numero_complet', 'client__nom', 'client__nif']
    readonly_fields = ['numero_complet', 'base_imponible', 'total_iva', 'total_irpf', 'total', 'verifactu_enviat_en', 'verifactu_hash']
    inlines = [LiniaFacturaInline]
