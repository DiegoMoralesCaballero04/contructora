import hashlib
import uuid
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Oferta(models.Model):
    class Estat(models.TextChoices):
        BORRADOR    = 'BORRADOR',    _('Esborrany')
        EN_REVISIO  = 'EN_REVISIO',  _('En revisió')
        APROVADA    = 'APROVADA',    _('Aprovada')
        ENVIADA     = 'ENVIADA',     _('Enviada')
        GUANYADA    = 'GUANYADA',    _('Guanyada')
        PERDUDA     = 'PERDUDA',     _('Perduda')
        RETIRADA    = 'RETIRADA',    _('Retirada')

    class NivellRisc(models.TextChoices):
        BAIX  = 'BAIX',  _('Baix')
        MITJA = 'MITJA', _('Mitjà')
        ALT   = 'ALT',   _('Alt')

    licitacio = models.OneToOneField(
        'licitaciones.Licitacion',
        on_delete=models.CASCADE,
        related_name='oferta',
        verbose_name=_('Licitació'),
    )
    estat = models.CharField(
        max_length=20, choices=Estat.choices, default=Estat.BORRADOR,
        db_index=True, verbose_name=_('Estat'),
    )
    responsable = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='ofertes_responsable', verbose_name=_('Responsable'),
    )
    revisor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='ofertes_revisor', verbose_name=_('Revisor'),
    )

    preu_oferta = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name=_('Preu oferta (€)'),
    )
    preu_optim_calculat = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name=_("Preu òptim calculat (€)"),
    )
    puntuacio_economica = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_('Puntuació econòmica estimada'),
    )
    puntuacio_tecnica = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_('Puntuació tècnica estimada'),
    )
    puntuacio_total = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name=_('Puntuació total estimada'),
    )

    nivell_risc = models.CharField(
        max_length=10, choices=NivellRisc.choices, default=NivellRisc.MITJA,
        verbose_name=_('Nivell de risc'),
    )
    factors_risc = models.JSONField(default=list, verbose_name=_('Factors de risc'))
    fortaleses = models.JSONField(default=list, verbose_name=_('Fortaleses'))
    debilitats = models.JSONField(default=list, verbose_name=_('Debilitats'))

    notes_internes = models.TextField(blank=True, verbose_name=_('Notes internes'))
    justificacio_preu = models.TextField(blank=True, verbose_name=_('Justificació del preu'))

    pdf_oferta_s3_key = models.CharField(max_length=500, blank=True, verbose_name=_('PDF oferta S3'))
    pdf_tecnica_s3_key = models.CharField(max_length=500, blank=True, verbose_name=_('PDF tècnica S3'))
    pdf_seguretat_s3_key = models.CharField(max_length=500, blank=True, verbose_name=_('PDF pla seguretat S3'))

    data_presentacio = models.DateTimeField(null=True, blank=True, verbose_name=_('Data presentació'))
    data_resolucio = models.DateTimeField(null=True, blank=True, verbose_name=_('Data resolució'))

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Oferta')
        verbose_name_plural = _('Ofertes')
        ordering = ['-creada_en']

    def __str__(self):
        return f'Oferta #{self.pk} — {self.licitacio.titol[:60]}'

    @property
    def marge_estimat(self):
        if self.preu_oferta and self.pressupost_cost_total:
            return float(self.preu_oferta) - float(self.pressupost_cost_total)
        return None

    @property
    def pressupost_cost_total(self):
        total = self.pressupostos.filter(actiu=True).aggregate(
            total=models.Sum('cost_total')
        )['total']
        return total or 0

    def transicionar_estat(self, nou_estat: str, user=None):
        """State machine with allowed transitions."""
        transicions = {
            self.Estat.BORRADOR:   [self.Estat.EN_REVISIO, self.Estat.RETIRADA],
            self.Estat.EN_REVISIO: [self.Estat.APROVADA, self.Estat.BORRADOR],
            self.Estat.APROVADA:   [self.Estat.ENVIADA, self.Estat.BORRADOR],
            self.Estat.ENVIADA:    [self.Estat.GUANYADA, self.Estat.PERDUDA, self.Estat.RETIRADA],
        }
        allowed = transicions.get(self.estat, [])
        if nou_estat not in allowed:
            raise ValueError(
                f"Transició no permesa: {self.estat} → {nou_estat}. Permeses: {allowed}"
            )
        self.estat = nou_estat
        if nou_estat == self.Estat.ENVIADA:
            self.data_presentacio = timezone.now()
            self.licitacio.estado = 'PRESENTADA'
            self.licitacio.save(update_fields=['estado'])
        elif nou_estat in (self.Estat.GUANYADA, self.Estat.PERDUDA):
            self.data_resolucio = timezone.now()
            if nou_estat == self.Estat.GUANYADA:
                self.licitacio.estado = 'ADJUDICADA'
                self.licitacio.save(update_fields=['estado'])
        self.save(update_fields=['estat', 'data_presentacio', 'data_resolucio', 'actualitzada_en'])


class VersioOferta(models.Model):
    oferta = models.ForeignKey(
        Oferta, on_delete=models.CASCADE, related_name='versions',
    )
    numero_versio = models.PositiveIntegerField()
    snap_data = models.JSONField()
    creada_per = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL,
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-numero_versio']
        unique_together = [('oferta', 'numero_versio')]

    def __str__(self):
        return f'Oferta #{self.oferta_id} v{self.numero_versio}'


class Pressupost(models.Model):
    oferta = models.ForeignKey(
        Oferta, on_delete=models.CASCADE, related_name='pressupostos',
    )
    titol = models.CharField(max_length=200, verbose_name=_('Títol'))
    versio = models.PositiveIntegerField(default=1)
    actiu = models.BooleanField(default=True, db_index=True)
    cost_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-versio']
        verbose_name = _('Pressupost')
        verbose_name_plural = _('Pressupostos')

    def __str__(self):
        return f'{self.titol} v{self.versio}'

    def recalcular_total(self):
        total = self.linies.aggregate(t=models.Sum(
            models.F('quantitat') * models.F('cost_unitari'),
            output_field=models.DecimalField()
        ))['t'] or 0
        self.cost_total = total
        self.save(update_fields=['cost_total', 'actualitzada_en'])


class LiniaPressupost(models.Model):
    class Tipus(models.TextChoices):
        MA_DOBRA     = 'MA_DOBRA',     _("Mà d'obra")
        MATERIALS    = 'MATERIALS',    _('Materials')
        SUBCONTRACTA = 'SUBCONTRACTA', _('Subcontracta')
        EQUIPAMENT   = 'EQUIPAMENT',   _('Equipament')
        INDIRECT     = 'INDIRECT',     _('Costos indirectes')
        ALTRES       = 'ALTRES',       _('Altres')

    pressupost = models.ForeignKey(
        Pressupost, on_delete=models.CASCADE, related_name='linies',
    )
    tipus = models.CharField(max_length=20, choices=Tipus.choices)
    descripcio = models.CharField(max_length=500)
    unitat = models.CharField(max_length=50, blank=True)
    quantitat = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    cost_unitari = models.DecimalField(max_digits=12, decimal_places=2)
    subcontractista = models.ForeignKey(
        'licitaciones.ContacteProvincial', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='linies_pressupost',
    )
    ordre = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['ordre', 'id']

    def __str__(self):
        return self.descripcio

    @property
    def cost_total(self):
        return self.quantitat * self.cost_unitari

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.pressupost.recalcular_total()


class SolicitudSubcontractista(models.Model):
    class Estat(models.TextChoices):
        PENDENT   = 'PENDENT',   _('Pendent')
        ENVIADA   = 'ENVIADA',   _('Enviada')
        REBUDA    = 'REBUDA',    _('Rebuda')
        ACCEPTADA = 'ACCEPTADA', _('Acceptada')
        REBUTJADA = 'REBUTJADA', _('Rebutjada')

    oferta = models.ForeignKey(
        Oferta, on_delete=models.CASCADE, related_name='solicituds_subcontractista',
    )
    contacte = models.ForeignKey(
        'licitaciones.ContacteProvincial', on_delete=models.CASCADE,
    )
    partides = models.JSONField(default=list, verbose_name=_('Partides sol·licitades'))
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.PENDENT)
    preu_resposta = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes_resposta = models.TextField(blank=True)
    token_resposta = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    enviada_en = models.DateTimeField(null=True, blank=True)
    resposta_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Sol·licitud subcontractista')

    def __str__(self):
        return f'{self.contacte} → Oferta #{self.oferta_id}'


class PlaSeguretat(models.Model):
    oferta = models.OneToOneField(
        Oferta, on_delete=models.CASCADE, related_name='pla_seguretat',
    )
    partides_obra = models.JSONField(default=list, verbose_name=_('Partides obra'))
    contingut_ia = models.TextField(blank=True, verbose_name=_('Contingut generat per IA'))
    contingut_revisat = models.TextField(blank=True, verbose_name=_('Contingut revisat'))
    prompt_versio = models.CharField(max_length=20, default='v1')
    model_usat = models.CharField(max_length=100, blank=True)
    validat = models.BooleanField(default=False)
    validat_per = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
    )
    validat_en = models.DateTimeField(null=True, blank=True)
    pdf_s3_key = models.CharField(max_length=500, blank=True)
    generat_en = models.DateTimeField(auto_now_add=True)
    actualitzat_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Pla de Seguretat i Salut')

    def __str__(self):
        return f'PSS Oferta #{self.oferta_id}'
