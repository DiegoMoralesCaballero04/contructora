from django.db import models
from django.core.exceptions import ValidationError


class ScrapingTemplate(models.Model):
    nom = models.CharField(max_length=200, default='Default')
    activa = models.BooleanField(default=True, db_index=True)

    importe_min = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    importe_max = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    provincies = models.JSONField(default=list, blank=True)

    tipus_contracte = models.JSONField(default=list, blank=True)

    procediments = models.JSONField(default=list, blank=True)

    cpv_inclosos = models.JSONField(default=list, blank=True)

    max_pagines = models.IntegerField(default=10)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Plantilla de scraping'
        verbose_name_plural = 'Plantilles de scraping'

    def __str__(self):
        return self.nom

    def clean(self):
        if ScrapingTemplate.objects.exclude(pk=self.pk).exists():
            raise ValidationError('Solo puede existir una plantilla de scraping.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_singleton(cls):
        template, _ = cls.objects.get_or_create(pk=1, defaults={'nom': 'Default'})
        return template

    def to_filters(self) -> dict:
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
