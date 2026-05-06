from django.contrib import admin
from .models import DocumentEmbedding, ConsultaRAG


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('font_tipus', 'font_id', 'numero_chunk', 'embedding_dim', 'model_embedding', 'creada_en')
    list_filter = ('font_tipus', 'model_embedding')
    search_fields = ('font_id', 'text_chunk')
    readonly_fields = ('id', 'sha256_chunk', 'embedding_dim', 'creada_en')

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConsultaRAG)
class ConsultaRAGAdmin(admin.ModelAdmin):
    list_display = ('pk', 'usuari', 'pregunta_short', 'estat', 'temps_ms', 'valoracio', 'creada_en')
    list_filter = ('estat', 'valoracio')
    search_fields = ('pregunta', 'resposta')
    readonly_fields = (
        'usuari', 'pregunta', 'filtres', 'context_recuperat',
        'resposta', 'fonts_citades', 'model_usat', 'temps_ms',
        'estat', 'error_msg', 'creada_en',
    )

    @admin.display(description='Pregunta')
    def pregunta_short(self, obj):
        return obj.pregunta[:80]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
