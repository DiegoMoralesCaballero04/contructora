from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _


class CalendariConfig(models.Model):
    """Per-user Microsoft Calendar OAuth2 credentials and preferences."""
    usuari = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='calendari_config',
    )
    ms_access_token = models.TextField(blank=True)
    ms_refresh_token = models.TextField(blank=True)
    ms_token_expiry = models.DateTimeField(null=True, blank=True)
    ms_calendar_id = models.CharField(max_length=200, blank=True)

    sincronitzar_licitacions = models.BooleanField(default=True)
    sincronitzar_ofertes = models.BooleanField(default=True)
    dies_avis_previ = models.PositiveIntegerField(default=3)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Configuració calendari')

    def __str__(self):
        return f'CalendariConfig — {self.usuari.username}'

    @property
    def esta_connectat(self):
        return bool(self.ms_access_token and self.ms_refresh_token)


class Esdeveniment(models.Model):
    class TipusEsdeveniment(models.TextChoices):
        TERMINI_LICITACIO  = 'TERMINI_LICITACIO',  _('Termini licitació')
        REUNIO_INTERNA     = 'REUNIO_INTERNA',      _('Reunió interna')
        PRESENTACIO_OFERTA = 'PRESENTACIO_OFERTA',  _('Presentació oferta')
        APERTURA_PLIQUES   = 'APERTURA_PLIQUES',    _('Obertura de pliques')
        SEGUIMENT          = 'SEGUIMENT',            _('Seguiment')
        ALTRES             = 'ALTRES',               _('Altres')

    class Estat(models.TextChoices):
        PENDENT   = 'PENDENT',   _('Pendent')
        SINCRONIT  = 'SINCRONIT', _('Sincronitzat')
        ERROR     = 'ERROR',     _('Error sincronització')
        CANCEL_LAT = 'CANCEL_LAT', _('Cancel·lat')

    licitacio = models.ForeignKey(
        'licitaciones.Licitacion', null=True, blank=True,
        on_delete=models.CASCADE, related_name='esdeveniments',
    )
    oferta = models.ForeignKey(
        'ofertes.Oferta', null=True, blank=True,
        on_delete=models.CASCADE, related_name='esdeveniments',
    )
    creador = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='esdeveniments_creats',
    )
    assistents = models.ManyToManyField(
        User, blank=True, related_name='esdeveniments_assignats',
    )

    tipus = models.CharField(max_length=30, choices=TipusEsdeveniment.choices)
    titol = models.CharField(max_length=300)
    descripcio = models.TextField(blank=True)
    ubicacio = models.CharField(max_length=300, blank=True)

    inici = models.DateTimeField(db_index=True)
    fi = models.DateTimeField()
    tot_el_dia = models.BooleanField(default=False)

    recordatori_minuts = models.PositiveIntegerField(default=60)

    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PENDENT)
    ms_event_id = models.CharField(max_length=500, blank=True)
    error_msg = models.TextField(blank=True)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Esdeveniment')
        verbose_name_plural = _('Esdeveniments')
        ordering = ['inici']
        indexes = [
            models.Index(fields=['inici', 'fi']),
            models.Index(fields=['estat']),
        ]

    def __str__(self):
        return f'{self.get_tipus_display()} — {self.titol[:60]} ({self.inici:%d/%m/%Y})'
