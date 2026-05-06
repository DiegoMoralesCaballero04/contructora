from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


IVA_CHOICES = [
    (Decimal('0.00'),  '0 %'),
    (Decimal('4.00'),  '4 %'),
    (Decimal('10.00'), '10 %'),
    (Decimal('21.00'), '21 %'),
]


class Client(models.Model):
    nom = models.CharField(max_length=300, verbose_name=_('Nom / Raó social'))
    nif = models.CharField(max_length=20, blank=True, verbose_name='NIF / CIF')
    email = models.EmailField(blank=True)
    telefon = models.CharField(max_length=30, blank=True)
    adreca = models.CharField(max_length=300, blank=True, verbose_name=_('Adreça'))
    poblacio = models.CharField(max_length=100, blank=True, verbose_name=_('Població'))
    codi_postal = models.CharField(max_length=10, blank=True)
    provincia = models.CharField(max_length=100, blank=True, verbose_name=_('Província'))
    pais = models.CharField(max_length=100, default='España', verbose_name=_('País'))
    actiu = models.BooleanField(default=True, verbose_name=_('Actiu'))
    notes = models.TextField(blank=True)
    creat_en = models.DateTimeField(auto_now_add=True)
    actualitzat_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Pedido(models.Model):
    class Estat(models.TextChoices):
        ESBORRANY  = 'ESBORRANY',  _('Esborrany')
        CONFIRMAT  = 'CONFIRMAT',  _('Confirmat')
        EN_CURS    = 'EN_CURS',    _('En curs')
        COMPLETAT  = 'COMPLETAT',  _('Completat')
        CANCEL_LAT = 'CANCEL_LAT', _('Cancel·lat')

    numero = models.CharField(max_length=50, unique=True, verbose_name=_('Número'))
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='pedidos')
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY, db_index=True)
    data = models.DateField(default=timezone.localdate, verbose_name=_('Data'))
    data_entrega = models.DateField(null=True, blank=True, verbose_name=_('Data d\'entrega'))
    referencia_client = models.CharField(max_length=100, blank=True, verbose_name=_('Ref. client'))
    notes = models.TextField(blank=True)
    creat_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='pedidos_creats')
    creat_en = models.DateTimeField(auto_now_add=True)
    actualitzat_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Pedido')
        verbose_name_plural = _('Pedidos')
        ordering = ['-data', '-creat_en']

    def __str__(self):
        return f'Pedido {self.numero} — {self.client}'

    @property
    def total(self):
        return sum(l.subtotal for l in self.linies.all())


class LiniaPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='linies')
    descripcio = models.CharField(max_length=500, verbose_name=_('Descripció'))
    quantitat = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('1'), validators=[MinValueValidator(Decimal('0.001'))])
    preu_unitari = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('Preu unitari'))
    descompte = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name=_('Descompte %'))
    iva = models.DecimalField(max_digits=5, decimal_places=2, choices=IVA_CHOICES, default=Decimal('21.00'), verbose_name='IVA %')
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'id']

    @property
    def base_imponible(self):
        return self.quantitat * self.preu_unitari * (1 - self.descompte / 100)

    @property
    def subtotal(self):
        return self.base_imponible * (1 + self.iva / 100)


class Albara(models.Model):
    class Estat(models.TextChoices):
        ESBORRANY  = 'ESBORRANY',  _('Esborrany')
        EMÈS       = 'EMÈS',       _('Emès')
        FACTURAT   = 'FACTURAT',   _('Facturat')

    numero = models.CharField(max_length=50, unique=True, verbose_name=_('Número'))
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='albarans')
    pedido = models.ForeignKey(Pedido, null=True, blank=True, on_delete=models.SET_NULL, related_name='albarans')
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY, db_index=True)
    data = models.DateField(default=timezone.localdate, verbose_name=_('Data'))
    notes = models.TextField(blank=True)
    creat_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='albarans_creats')
    creat_en = models.DateTimeField(auto_now_add=True)
    actualitzat_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Albarà')
        verbose_name_plural = _('Albarans')
        ordering = ['-data', '-creat_en']

    def __str__(self):
        return f'Albarà {self.numero} — {self.client}'


class LiniaAlbara(models.Model):
    albara = models.ForeignKey(Albara, on_delete=models.CASCADE, related_name='linies')
    descripcio = models.CharField(max_length=500, verbose_name=_('Descripció'))
    quantitat = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('1'), validators=[MinValueValidator(Decimal('0.001'))])
    preu_unitari = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('Preu unitari'))
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'id']

    @property
    def subtotal(self):
        return self.quantitat * self.preu_unitari


class Factura(models.Model):
    class Estat(models.TextChoices):
        ESBORRANY  = 'ESBORRANY',  _('Esborrany')
        EMESA      = 'EMESA',      _('Emesa')
        COBRADA    = 'COBRADA',    _('Cobrada')
        VENÇUDA    = 'VENÇUDA',    _('Vençuda')
        ANUL_LADA  = 'ANUL_LADA',  _('Anul·lada')

    class TipusFactura(models.TextChoices):
        ORDINARIA  = 'ORDINARIA',  _('Ordinària')
        RECTIFICATIVA = 'RECTIFICATIVA', _('Rectificativa')
        PROFORMA   = 'PROFORMA',   _('Proforma')

    serie = models.CharField(max_length=10, default='F', verbose_name=_('Sèrie'))
    numero = models.PositiveIntegerField(verbose_name=_('Número'))
    numero_complet = models.CharField(max_length=50, unique=True, editable=False, verbose_name=_('Número complet'))

    tipus = models.CharField(max_length=20, choices=TipusFactura.choices, default=TipusFactura.ORDINARIA)
    estat = models.CharField(max_length=20, choices=Estat.choices, default=Estat.ESBORRANY, db_index=True)

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='factures')
    albara = models.ForeignKey(Albara, null=True, blank=True, on_delete=models.SET_NULL, related_name='factures')
    pedido = models.ForeignKey(Pedido, null=True, blank=True, on_delete=models.SET_NULL, related_name='factures')

    data_emisio = models.DateField(default=timezone.localdate, verbose_name=_('Data emissió'))
    data_venciment = models.DateField(null=True, blank=True, verbose_name=_('Data venciment'))

    base_imponible = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'), verbose_name=_('Base imposable'))
    total_iva = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'), verbose_name='Total IVA')
    total_irpf = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'), verbose_name='Retenció IRPF')
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'), verbose_name=_('Total'))

    irpf_percentatge = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name='IRPF %')

    notes = models.TextField(blank=True)
    notes_internes = models.TextField(blank=True)

    document_adjunt = models.FileField(
        upload_to='erp/factures/%Y/%m/',
        null=True, blank=True,
        verbose_name=_('Document adjunt (PDF/imatge)'),
    )
    extraccio_ia = models.JSONField(
        default=dict, blank=True,
        verbose_name=_('Dades extretes per IA'),
    )

    verifactu = models.BooleanField(
        default=False,
        verbose_name='Enviar a VerifactuRE',
        help_text='Enviar al sistema de verificació de factures de l\'AEAT (Reial Decret 1007/2023)',
    )
    verifactu_enviat_en = models.DateTimeField(null=True, blank=True, editable=False)
    verifactu_hash = models.CharField(max_length=64, blank=True, editable=False)

    factura_rectificada = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='rectificatives', verbose_name=_('Factura rectificada'),
    )

    creat_per = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='factures_creades')
    creat_en = models.DateTimeField(auto_now_add=True)
    actualitzat_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Factura')
        verbose_name_plural = _('Factures')
        ordering = ['-data_emisio', '-numero']
        constraints = [
            models.UniqueConstraint(fields=['serie', 'numero'], name='unique_serie_numero'),
        ]

    def __str__(self):
        return self.numero_complet or f'{self.serie}{self.numero:06d}'

    def save(self, *args, **kwargs):
        if not self.numero:
            last = Factura.objects.filter(serie=self.serie).order_by('-numero').first()
            self.numero = (last.numero + 1) if last else 1
        self.numero_complet = f'{self.serie}{self.numero:06d}'
        self.recalcular_totals()
        super().save(*args, **kwargs)

    def recalcular_totals(self):
        base = Decimal('0')
        iva_total = Decimal('0')
        for l in self.linies.all():
            base += l.base_imponible
            iva_total += l.import_iva
        self.base_imponible = base.quantize(Decimal('0.01'))
        self.total_iva = iva_total.quantize(Decimal('0.01'))
        retencio = (base * self.irpf_percentatge / 100).quantize(Decimal('0.01'))
        self.total_irpf = retencio
        self.total = (base + iva_total - retencio).quantize(Decimal('0.01'))


class LiniaFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='linies')
    descripcio = models.CharField(max_length=500, verbose_name=_('Descripció'))
    quantitat = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal('1'), validators=[MinValueValidator(Decimal('0.001'))])
    preu_unitari = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), verbose_name=_('Preu unitari'))
    descompte = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0'), verbose_name=_('Descompte %'))
    iva = models.DecimalField(max_digits=5, decimal_places=2, choices=IVA_CHOICES, default=Decimal('21.00'), verbose_name='IVA %')
    ordre = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordre', 'id']

    @property
    def base_imponible(self):
        return (self.quantitat * self.preu_unitari * (1 - self.descompte / 100)).quantize(Decimal('0.01'))

    @property
    def import_iva(self):
        return (self.base_imponible * self.iva / 100).quantize(Decimal('0.01'))

    @property
    def subtotal(self):
        return self.base_imponible + self.import_iva
