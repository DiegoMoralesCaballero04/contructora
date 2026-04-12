from django.db import models


class ScrapingJob(models.Model):
    class Estado(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        EN_CURS = 'EN_CURS', 'En curs'
        COMPLETAT = 'COMPLETAT', 'Completat'
        ERROR = 'ERROR', 'Error'

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
