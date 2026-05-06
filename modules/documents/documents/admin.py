from django.contrib import admin
from .models import Document, VersioDocument, CategoriaDocument, AccesDocument, PermisDocument


@admin.register(CategoriaDocument)
class CategoriaDocumentAdmin(admin.ModelAdmin):
    list_display = ('codi', 'nom', 'retencio_anys', 'requereix_aprovacio')
    ordering = ('ordre', 'nom')


class VersioDocumentInline(admin.TabularInline):
    model = VersioDocument
    extra = 0
    readonly_fields = ('numero_versio', 's3_key', 'sha256', 'mida_bytes', 'creada_per', 'creada_en')
    can_delete = False


class PermisInline(admin.TabularInline):
    model = PermisDocument
    extra = 1


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'categoria', 'tipus', 'estat', 'mida_bytes', 'data_caducitat', 'pujat_per')
    list_filter = ('estat', 'tipus', 'categoria')
    search_fields = ('nom', 'descripcio')
    readonly_fields = ('sha256', 'mida_bytes', 'nom_fitxer_original', 'mime_type', 'creada_en')
    inlines = [VersioDocumentInline, PermisInline]


@admin.register(AccesDocument)
class AccesDocumentAdmin(admin.ModelAdmin):
    list_display = ('document', 'usuari', 'accio', 'ip_address', 'timestamp')
    list_filter = ('accio',)
    readonly_fields = ('document', 'usuari', 'accio', 'ip_address', 'user_agent', 'versio', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
