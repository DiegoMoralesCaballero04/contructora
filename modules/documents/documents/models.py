import hashlib
import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class CategoriaDocument(models.Model):
    nom = models.CharField(max_length=100)
    codi = models.CharField(max_length=20, unique=True)
    descripcio = models.TextField(blank=True)
    pare = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='fills',
    )
    retencio_anys = models.PositiveIntegerField(
        default=5,
        help_text='Anys de retenció obligatoria (ISO 9001/14001)',
    )
    requereix_aprovacio = models.BooleanField(default=False)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('Categoria document')
        ordering = ['ordre', 'nom']

    def __str__(self):
        return f'{self.codi} — {self.nom}'


class Document(models.Model):
    class Estat(models.TextChoices):
        PUJANT   = 'PUJANT',   _('Pujant')
        ACTIU    = 'ACTIU',    _('Actiu')
        ARXIVAT  = 'ARXIVAT',  _('Arxivat')
        ELIMINAT = 'ELIMINAT', _('Eliminat')

    class Tipus(models.TextChoices):
        PDF          = 'PDF',          'PDF'
        WORD         = 'WORD',         'Word'
        EXCEL        = 'EXCEL',        'Excel'
        IMATGE       = 'IMATGE',       _('Imatge')
        VIDEO        = 'VIDEO',        _('Vídeo')
        ALTRES       = 'ALTRES',       _('Altres')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=300, verbose_name=_('Nom document'))
    descripcio = models.TextField(blank=True)
    categoria = models.ForeignKey(
        CategoriaDocument, on_delete=models.PROTECT, related_name='documents',
    )
    tipus = models.CharField(max_length=20, choices=Tipus.choices, default=Tipus.ALTRES)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PUJANT, db_index=True)

    s3_key = models.CharField(max_length=500, unique=True)
    nom_fitxer_original = models.CharField(max_length=300)
    mida_bytes = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)

    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    s3_version_id = models.CharField(max_length=200, blank=True)

    metadades = models.JSONField(default=dict)
    etiquetes = models.JSONField(default=list)

    licitacio = models.ForeignKey(
        'licitaciones.Licitacion', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='documents',
    )
    oferta = models.ForeignKey(
        'ofertes.Oferta', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='documents',
    )

    pujat_per = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='documents_pujats',
    )
    propietari = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='documents_propietari',
    )

    data_document = models.DateField(null=True, blank=True)
    data_caducitat = models.DateField(null=True, blank=True, db_index=True)
    data_eliminacio_prevista = models.DateField(null=True, blank=True)

    versio_actual = models.ForeignKey(
        'VersioDocument', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
    )

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Document')
        verbose_name_plural = _('Documents')
        ordering = ['-creada_en']
        indexes = [
            models.Index(fields=['categoria', 'estat']),
            models.Index(fields=['data_caducitat']),
        ]

    def __str__(self):
        return self.nom

    @property
    def mida_llegible(self) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.mida_bytes < 1024:
                return f'{self.mida_bytes:.1f} {unit}'
            self.mida_bytes /= 1024
        return f'{self.mida_bytes:.1f} GB'


class VersioDocument(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='versions',
    )
    numero_versio = models.PositiveIntegerField()
    s3_key = models.CharField(max_length=500)
    s3_version_id = models.CharField(max_length=200, blank=True)
    sha256 = models.CharField(max_length=64)
    mida_bytes = models.BigIntegerField(default=0)
    notes_versio = models.TextField(blank=True)
    creada_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-numero_versio']
        unique_together = [('document', 'numero_versio')]

    def __str__(self):
        return f'{self.document.nom} v{self.numero_versio}'


class PermisDocument(models.Model):
    class Nivell(models.TextChoices):
        LECTURA  = 'LECTURA',  _('Lectura')
        EDICIO   = 'EDICIO',   _('Edició')
        ADMIN    = 'ADMIN',    _('Administrador')

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='permisos')
    usuari = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name='permisos_documents',
    )
    rol = models.CharField(
        max_length=20, blank=True,
        help_text='Rol de rrhh.UserProfile (ADMIN/JEFE/SUPERVISOR/TRABAJADOR)',
    )
    nivell = models.CharField(max_length=20, choices=Nivell.choices, default=Nivell.LECTURA)
    atorgat_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    atorgat_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Permís document')

    def __str__(self):
        subjecte = self.usuari.username if self.usuari else f'rol:{self.rol}'
        return f'{self.document.nom} — {subjecte} ({self.nivell})'


class AccesDocument(models.Model):
    """Immutable access log for ISO 9001 traceability."""
    class Accio(models.TextChoices):
        DESCARREGA = 'DESCARREGA', _('Descàrrega')
        VISUALITZA = 'VISUALITZA', _('Visualització')
        EDICIO     = 'EDICIO',     _('Edició')
        ELIMINACIO = 'ELIMINACIO', _('Eliminació')

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='accessos')
    usuari = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    accio = models.CharField(max_length=20, choices=Accio.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    versio = models.ForeignKey(VersioDocument, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Accés document')
