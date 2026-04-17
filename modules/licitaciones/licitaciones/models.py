from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ─── Province data ───────────────────────────────────────────────────────────

PROVINCIES_ESPANYA = {
    'Andalucía':          ['Almería', 'Cádiz', 'Córdoba', 'Granada', 'Huelva', 'Jaén', 'Málaga', 'Sevilla'],
    'Aragón':             ['Huesca', 'Teruel', 'Zaragoza'],
    'Asturias':           ['Asturias'],
    'Illes Balears':      ['Illes Balears'],
    'Canarias':           ['Las Palmas', 'Santa Cruz de Tenerife'],
    'Cantabria':          ['Cantabria'],
    'Castilla-La Mancha': ['Albacete', 'Ciudad Real', 'Cuenca', 'Guadalajara', 'Toledo'],
    'Castilla y León':    ['Ávila', 'Burgos', 'León', 'Palencia', 'Salamanca', 'Segovia', 'Soria', 'Valladolid', 'Zamora'],
    'Catalunya':          ['Barcelona', 'Girona', 'Lleida', 'Tarragona'],
    'Comunitat Valenciana': ['Alicante', 'Castellón', 'Valencia'],
    'Extremadura':        ['Badajoz', 'Cáceres'],
    'Galicia':            ['A Coruña', 'Lugo', 'Ourense', 'Pontevedra'],
    'La Rioja':           ['La Rioja'],
    'Madrid':             ['Madrid'],
    'Murcia':             ['Murcia'],
    'Navarra':            ['Navarra'],
    'País Vasco':         ['Álava', 'Gipuzkoa', 'Bizkaia'],
    'Ciudades Autónomas': ['Ceuta', 'Melilla'],
}


class Organismo(models.Model):
    nombre = models.CharField(max_length=500)
    nif = models.CharField(max_length=20, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=200, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Organisme'
        verbose_name_plural = 'Organismes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Licitacion(models.Model):
    class Estado(models.TextChoices):
        NUEVA          = 'NUEVA',          _('Nueva')
        REVISADA       = 'REVISADA',       _('Revisada')
        DESCARTADA     = 'DESCARTADA',     _('Descartada')
        EN_PREPARACION = 'EN_PREPARACION', _('En preparación')
        PRESENTADA     = 'PRESENTADA',     _('Presentada')
        ADJUDICADA     = 'ADJUDICADA',     _('Adjudicada')
        DESIERTA       = 'DESIERTA',       _('Desierta')

    class Procedimiento(models.TextChoices):
        ABIERTO      = 'ABIERTO',      _('Abierto')
        RESTRINGIDO  = 'RESTRINGIDO',  _('Restringido')
        NEGOCIADO    = 'NEGOCIADO',    _('Negociado')
        SIMPLIFICADO = 'SIMPLIFICADO', _('Simplificado')
        OTRO         = 'OTRO',         _('Otro')

    # Identificadors
    expediente_id = models.CharField(max_length=200, unique=True, db_index=True)
    url_origen = models.URLField(max_length=1000)

    # Dades bàsiques
    titulo = models.CharField(max_length=1000)
    organismo = models.ForeignKey(
        Organismo, on_delete=models.SET_NULL, null=True, related_name='licitaciones'
    )
    provincia = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=200, blank=True)

    # Econòmics
    importe_base = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    importe_iva = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    # Procediment i terminis
    procedimiento = models.CharField(
        max_length=20, choices=Procedimiento.choices, default=Procedimiento.ABIERTO
    )
    fecha_publicacion = models.DateField(null=True, blank=True)
    fecha_limite_oferta = models.DateTimeField(null=True, blank=True)
    plazo_ejecucion_dias = models.IntegerField(null=True, blank=True)

    # Classificació empresarial
    clasificacion_grupo = models.CharField(max_length=5, blank=True)
    clasificacion_subgrupo = models.CharField(max_length=5, blank=True)
    clasificacion_categoria = models.CharField(max_length=5, blank=True)

    # PDF a S3
    pdf_pliego_s3_key = models.CharField(max_length=500, blank=True)
    pdf_pliego_url = models.URLField(max_length=1000, blank=True)
    pdf_descargado = models.BooleanField(default=False)

    # Estat intern
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.NUEVA, db_index=True
    )
    es_relevante = models.BooleanField(default=True)
    notas = models.TextField(blank=True)

    # Metadades
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    # Referència al document MongoDB (raw data)
    mongo_id = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = 'Licitació'
        verbose_name_plural = 'Licitacions'
        ordering = ['-fecha_publicacion', '-creado_en']
        indexes = [
            models.Index(fields=['estado', 'provincia']),
            models.Index(fields=['fecha_publicacion']),
            models.Index(fields=['importe_base']),
        ]

    def __str__(self):
        return f'{self.expediente_id} — {self.titulo[:80]}'

    @property
    def dias_restantes(self):
        if self.fecha_limite_oferta:
            delta = self.fecha_limite_oferta.date() - timezone.now().date()
            return delta.days
        return None

    @property
    def tiene_extraccion(self):
        return hasattr(self, 'extraccion') and self.extraccion is not None


class InformeIntern(models.Model):
    class Recomendacio(models.TextChoices):
        PRESENTAR = 'PRESENTAR', _('Presentar oferta')
        DESCARTAR = 'DESCARTAR', _('Descartar')
        ESTUDIAR  = 'ESTUDIAR',  _('Estudiar más')

    licitacion      = models.ForeignKey(Licitacion, on_delete=models.CASCADE, related_name='informes')
    autor           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='informes')
    recomendacio    = models.CharField(max_length=20, choices=Recomendacio.choices, default=Recomendacio.ESTUDIAR)
    puntuacio       = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-10
    analisi_tecnica = models.TextField(blank=True)
    punts_forts     = models.TextField(blank=True)
    punts_febles    = models.TextField(blank=True)
    observacions    = models.TextField(blank=True)
    # PDF generat automàticament per a trazabilitat (estats PRESENTADA/ADJUDICADA/DESIERTA)
    pdf_s3_key      = models.CharField(max_length=500, blank=True)
    pdf_s3_url      = models.URLField(max_length=1000, blank=True)
    creado_en       = models.DateTimeField(auto_now_add=True)
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Informe intern'
        verbose_name_plural = 'Informes interns'
        ordering = ['-creado_en']

    def __str__(self):
        return f'Informe {self.licitacion.expediente_id} — {self.autor}'

    @property
    def recomendacio_color(self):
        return {'PRESENTAR': 'success', 'DESCARTAR': 'danger', 'ESTUDIAR': 'warning'}.get(self.recomendacio, 'secondary')


class CriterioAdjudicacion(models.Model):
    licitacion = models.ForeignKey(
        Licitacion, on_delete=models.CASCADE, related_name='criterios'
    )
    nombre = models.CharField(max_length=500)
    puntuacion_maxima = models.DecimalField(max_digits=6, decimal_places=2)
    formula = models.TextField(blank=True)
    es_economico = models.BooleanField(default=False)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Criteri d\'adjudicació'
        verbose_name_plural = 'Criteris d\'adjudicació'
        ordering = ['orden']

    def __str__(self):
        return f'{self.nombre} ({self.puntuacion_maxima} pts)'


# ─── Company config (singleton) ───────────────────────────────────────────────

class ConfigEmpresa(models.Model):
    """Singleton: company-wide province preferences."""
    provincia_principal  = models.CharField(max_length=100, blank=True)
    provincies_favorites = models.JSONField(default=list)
    municipis_favorites  = models.JSONField(default=list)

    class Meta:
        verbose_name = 'Configuració empresa'

    def __str__(self):
        return 'Configuració empresa'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def all_favorites(self):
        """Returns the full set of favourite provinces: principal + favorites."""
        provs = set(self.provincies_favorites)
        if self.provincia_principal:
            provs.add(self.provincia_principal)
        return provs

    def all_municipis(self):
        """Returns the set of favourite municipalities."""
        return set(self.municipis_favorites)


# ─── Provincial contacts ──────────────────────────────────────────────────────

class ContacteProvincial(models.Model):
    class Rol(models.TextChoices):
        SUBCONTRACTISTA = 'SUBCONTRACTISTA', _('Subcontratista')
        PROVEIDOR       = 'PROVEIDOR',       _('Proveedor')
        DELEGAT         = 'DELEGAT',         _('Delegado local')
        TECNIC          = 'TECNIC',          _('Técnico / Arquitecto')
        ALTRE           = 'ALTRE',           _('Otro')

    provincia  = models.CharField(max_length=100, db_index=True)
    nom        = models.CharField(max_length=200)
    empresa    = models.CharField(max_length=200, blank=True)
    rol        = models.CharField(max_length=20, choices=Rol.choices, default=Rol.ALTRE)
    telefon    = models.CharField(max_length=30, blank=True)
    email      = models.EmailField(blank=True)
    notes      = models.TextField(blank=True)
    creado_en  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Contacte provincial'
        verbose_name_plural = 'Contactes provincials'
        ordering = ['provincia', 'nom']

    def __str__(self):
        return f'{self.nom} ({self.provincia})'
