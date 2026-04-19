from django.contrib import admin
from django.utils.html import format_html

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    fields = (
        'nombre_empresa', 'direccion', 'ciudad', 'pais',
        'email_contacto', 'telefono', 'logo', 'logo_preview', 'descripcion',
    )
    readonly_fields = ('logo_preview',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height:80px;border-radius:4px;" />', obj.logo.url)
        return '—'
    logo_preview.short_description = 'Vista previa'

    def has_add_permission(self, request):
        return not Empresa.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
