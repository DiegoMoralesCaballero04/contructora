import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class EmpresaProspect(models.Model):
    """Potential client companies for marketing outreach."""
    class Sector(models.TextChoices):
        CONSTRUCCIO = 'CONSTRUCCIO', _('Construcció')
        ENGINYERIA  = 'ENGINYERIA',  _('Enginyeria')
        PROMOTORA   = 'PROMOTORA',   _('Promotora')
        ADMINISTRACIO = 'ADMINISTRACIO', _('Administració pública')
        AUTRES      = 'AUTRES',      _('Altres')

    class Origen(models.TextChoices):
        MANUAL      = 'MANUAL',      _('Manual')
        LICITACIO   = 'LICITACIO',   _('Licitació (organisme)')
        IMPORTACIO  = 'IMPORTACIO',  _('Importació')
        REFERENCIA  = 'REFERENCIA',  _('Referència')

    class Estat(models.TextChoices):
        PROSPECCIO  = 'PROSPECCIO',  _('Prospecció')
        CONTACTAT   = 'CONTACTAT',   _('Contactat')
        INTERESSAT  = 'INTERESSAT',  _('Interessat')
        CLIENT      = 'CLIENT',      _('Client')
        DESCARTAT   = 'DESCARTAT',   _('Descartat')

    nom = models.CharField(max_length=300)
    sector = models.CharField(max_length=30, choices=Sector.choices, default=Sector.CONSTRUCCIO)
    origen = models.CharField(max_length=20, choices=Origen.choices, default=Origen.MANUAL)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PROSPECCIO, db_index=True)

    email_principal = models.EmailField(blank=True)
    emails_alternatius = models.JSONField(default=list)
    telefon = models.CharField(max_length=30, blank=True)
    web = models.URLField(blank=True)
    direccio = models.CharField(max_length=300, blank=True)
    poblacio = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=50, blank=True)

    persona_contacte = models.CharField(max_length=200, blank=True)
    carrec_contacte = models.CharField(max_length=100, blank=True)

    scoring = models.FloatField(default=0.0, db_index=True)
    notes = models.TextField(blank=True)

    consentiment_gdpr = models.BooleanField(default=False)
    data_consentiment = models.DateTimeField(null=True, blank=True)
    baixa_voluntaria = models.BooleanField(default=False)
    data_baixa = models.DateTimeField(null=True, blank=True)
    token_baixa = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    licitacio_origen = models.ForeignKey(
        'licitaciones.Licitacion', null=True, blank=True, on_delete=models.SET_NULL,
    )
    assignat_a = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
    )

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Empresa prospecte')
        verbose_name_plural = _('Empreses prospecte')
        ordering = ['-scoring', '-creada_en']
        indexes = [
            models.Index(fields=['sector', 'estat']),
            models.Index(fields=['baixa_voluntaria']),
        ]

    def __str__(self):
        return self.nom

    @property
    def pot_rebre_emails(self) -> bool:
        return (
            bool(self.email_principal)
            and not self.baixa_voluntaria
            and self.consentiment_gdpr
        )


class PlantillaEmail(models.Model):
    class Tipus(models.TextChoices):
        PROSPECCIO      = 'PROSPECCIO',      _('Prospecció inicial')
        SEGUIMENT       = 'SEGUIMENT',       _('Seguiment')
        PRESENTACIO     = 'PRESENTACIO',     _('Presentació empresa')
        OFERTA_SERVEI   = 'OFERTA_SERVEI',   _('Oferta de servei')

    nom = models.CharField(max_length=200)
    tipus = models.CharField(max_length=30, choices=Tipus.choices)
    idioma = models.CharField(max_length=5, default='ca')
    assumpte = models.CharField(max_length=300)
    cos_text = models.TextField()
    cos_html = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    creada_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Plantilla email')

    def __str__(self):
        return f'{self.nom} ({self.get_tipus_display()})'


class CampanyaMarketing(models.Model):
    class Estat(models.TextChoices):
        ESBORRANY  = 'ESBORRANY',  _('Esborrany')
        PROGRAMADA = 'PROGRAMADA', _('Programada')
        EN_CURS    = 'EN_CURS',    _('En curs')
        COMPLETADA = 'COMPLETADA', _('Completada')
        PAUSADA    = 'PAUSADA',    _('Pausada')

    nom = models.CharField(max_length=200)
    plantilla = models.ForeignKey(PlantillaEmail, on_delete=models.PROTECT)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY)

    segments = models.JSONField(
        default=dict,
        help_text='Filtres: {"sector": ["CONSTRUCCIO"], "provincia": ["Valencia"], "scoring_min": 5.0}',
    )

    millorar_amb_ia = models.BooleanField(default=True)
    personalitzar_per_empresa = models.BooleanField(default=True)

    data_programada = models.DateTimeField(null=True, blank=True)

    total_destinataris = models.IntegerField(default=0)
    total_enviats = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)
    total_obertures = models.IntegerField(default=0)
    total_clics = models.IntegerField(default=0)

    creada_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    creada_en = models.DateTimeField(auto_now_add=True)
    iniciada_en = models.DateTimeField(null=True, blank=True)
    completada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Campanya marketing')
        ordering = ['-creada_en']

    def __str__(self):
        return self.nom

    @property
    def taxa_obertura(self) -> float:
        if self.total_enviats:
            return round(self.total_obertures / self.total_enviats * 100, 1)
        return 0.0


class EnviamentEmail(models.Model):
    class Estat(models.TextChoices):
        PENDENT  = 'PENDENT',  _('Pendent')
        ENVIANT  = 'ENVIANT',  _('Enviant')
        ENVIAT   = 'ENVIAT',   _('Enviat')
        ERROR    = 'ERROR',    _('Error')
        REBUTJAT = 'REBUTJAT', _('Rebutjat (bounce)')

    campanya = models.ForeignKey(
        CampanyaMarketing, on_delete=models.CASCADE, related_name='enviaments',
    )
    prospect = models.ForeignKey(
        EmpresaProspect, on_delete=models.CASCADE, related_name='enviaments',
    )

    assumpte_final = models.CharField(max_length=300)
    cos_final_text = models.TextField()
    cos_final_html = models.TextField(blank=True)

    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PENDENT, db_index=True)
    error_msg = models.TextField(blank=True)

    tracking_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    obert = models.BooleanField(default=False)
    obert_en = models.DateTimeField(null=True, blank=True)
    clicat = models.BooleanField(default=False)
    clicat_en = models.DateTimeField(null=True, blank=True)

    enviat_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Enviament email')
        unique_together = [('campanya', 'prospect')]
        indexes = [models.Index(fields=['estat', 'creada_en'])]
