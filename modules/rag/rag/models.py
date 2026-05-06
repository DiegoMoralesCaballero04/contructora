"""
RAG models.

Storage strategy:
  - DocumentEmbedding: PostgreSQL with pgvector extension for vector similarity search.
    If pgvector is not available, falls back to storing embeddings in MongoDB
    and doing in-Python cosine similarity (slower but no migration needed).
  - ConsultaRAG: query history in PostgreSQL.

pgvector setup (run once):
  CREATE EXTENSION IF NOT EXISTS vector;
"""
import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class DocumentEmbedding(models.Model):
    """
    Stores a text chunk + its embedding vector for RAG retrieval.

    For pgvector: use VectorField(dimensions=768) from pgvector.django.
    Currently stored as JSON array (portable fallback).
    Migrate to VectorField once pgvector extension is confirmed available.
    """
    class FontTipus(models.TextChoices):
        LICITACIO  = 'LICITACIO',  _('Licitació (PDF plec)')
        EXTRACCION = 'EXTRACCION', _('Extracció IA')
        DOCUMENT   = 'DOCUMENT',   _('Document intern')
        INFORME    = 'INFORME',    _('Informe intern')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    font_tipus = models.CharField(max_length=20, choices=FontTipus.choices, db_index=True)
    font_id = models.CharField(max_length=100, db_index=True)

    licitacio = models.ForeignKey(
        'licitaciones.Licitacion', null=True, blank=True,
        on_delete=models.CASCADE, related_name='embeddings',
    )
    document = models.ForeignKey(
        'documents.Document', null=True, blank=True,
        on_delete=models.CASCADE, related_name='embeddings',
    )

    numero_chunk = models.PositiveIntegerField(default=0)
    text_chunk = models.TextField()
    metadata = models.JSONField(default=dict)

    model_embedding = models.CharField(max_length=100, default='nomic-embed-text')
    embedding_dim = models.PositiveIntegerField(default=768)
    embedding = models.JSONField(default=list)

    sha256_chunk = models.CharField(max_length=64, db_index=True)

    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Embedding document')
        indexes = [
            models.Index(fields=['font_tipus', 'font_id']),
            models.Index(fields=['sha256_chunk']),
        ]
        unique_together = [('font_tipus', 'font_id', 'numero_chunk')]

    def __str__(self):
        return f'{self.font_tipus}:{self.font_id} chunk#{self.numero_chunk}'


class ConsultaRAG(models.Model):
    """Stores RAG query history for quality tracking and improvement."""
    class Estat(models.TextChoices):
        EN_CURS    = 'EN_CURS',    _('En curs')
        COMPLETADA = 'COMPLETADA', _('Completada')
        ERROR      = 'ERROR',      _('Error')

    usuari = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
    )
    pregunta = models.TextField()
    filtres = models.JSONField(default=dict)
    context_recuperat = models.JSONField(default=list)
    resposta = models.TextField(blank=True)
    fonts_citades = models.JSONField(default=list)
    model_usat = models.CharField(max_length=100, blank=True)
    temps_ms = models.IntegerField(default=0)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.EN_CURS)
    error_msg = models.TextField(blank=True)
    valoracio = models.IntegerField(null=True, blank=True, help_text='1-5')
    comentari_valoracio = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Consulta RAG')
        ordering = ['-creada_en']

    def __str__(self):
        return f'RAG #{self.pk}: {self.pregunta[:60]}'
