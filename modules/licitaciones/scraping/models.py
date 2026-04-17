from django.db import models


class ScrapingTemplate(models.Model):
    """
    Client-configurable scraping template.
    All filter fields are optional — empty means 'no filter'.
    The first active template is used by default when no template_id is provided.
    """
    nom = models.CharField(max_length=200)
    activa = models.BooleanField(default=True, db_index=True)

    # Amount range
    importe_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    importe_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    # Territory — list of province names, e.g. ["Valencia", "Alicante"]
    provincies = models.JSONField(default=list, blank=True)

    # Contract type codes (empty = all)
    # 1=Obras, 2=Concesión Obras, 3=Gestión Servicios, 4=Suministros, 5=Servicios, 6=Otros
    tipus_contracte = models.JSONField(default=list, blank=True)

    # Procedure codes (empty = all)
    # 1=Abierto, 2=Restringido, 4=Negociado s/publicidad, 7=Simplificado
    procediments = models.JSONField(default=list, blank=True)

    # CPV code prefixes to include (empty = all), e.g. ["45", "71"]
    cpv_inclosos = models.JSONField(default=list, blank=True)

    # Max pages to scrape per run
    max_pagines = models.IntegerField(default=10)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plantilla de scraping'
        verbose_name_plural = 'Plantilles de scraping'
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def to_filters(self) -> dict:
        """Return a filters dict ready for ContratacionesScraper."""
        filters = {}
        if self.importe_min is not None:
            filters['importe_min'] = float(self.importe_min)
        if self.importe_max is not None:
            filters['importe_max'] = float(self.importe_max)
        if self.provincies:
            filters['provincies'] = list(self.provincies)
        if self.tipus_contracte:
            filters['tipus_contracte'] = list(self.tipus_contracte)
        if self.procediments:
            filters['procediments'] = list(self.procediments)
        if self.cpv_inclosos:
            filters['cpv_inclosos'] = list(self.cpv_inclosos)
        return filters


class ScrapingJob(models.Model):
    class Estado(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        EN_CURS = 'EN_CURS', 'En curs'
        COMPLETAT = 'COMPLETAT', 'Completat'
        ERROR = 'ERROR', 'Error'

    template = models.ForeignKey(
        ScrapingTemplate, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='jobs',
    )
    iniciat_en = models.DateTimeField(auto_now_add=True)
    finalitzat_en = models.DateTimeField(null=True, blank=True)
    estat = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDENT)

    total_trobades = models.IntegerField(default=0)
    noves_insertades = models.IntegerField(default=0)
    actualitzades = models.IntegerField(default=0)
    descartades = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)

    detalls_error = models.TextField(blank=True)
    filtres_aplicats = models.JSONField(default=dict)

    class Meta:
        verbose_name = 'Treball de scraping'
        verbose_name_plural = 'Treballs de scraping'
        ordering = ['-iniciat_en']

    def __str__(self):
        return f'ScrapingJob #{self.pk} — {self.estat} ({self.iniciat_en:%d/%m/%Y %H:%M})'

    @property
    def duracio_segons(self):
        if self.finalitzat_en:
            return (self.finalitzat_en - self.iniciat_en).total_seconds()
        return None
