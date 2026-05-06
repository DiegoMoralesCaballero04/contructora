from django.db import models


class Extraccion(models.Model):
    class Estado(models.TextChoices):
        PENDENT = 'PENDENT', 'Pendent'
        EN_CURS = 'EN_CURS', 'En curs'
        OK = 'OK', 'Correcte'
        ERROR = 'ERROR', 'Error'
        REVISAR = 'REVISAR', 'Cal revisar'

    licitacio = models.OneToOneField(
        'licitaciones.Licitacion',
        on_delete=models.CASCADE,
        related_name='extraccion',
    )
    estat = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDENT)

    # Dades extretes pel LLM (en PostgreSQL per a consultes)
    objecte_extret = models.TextField(blank=True)
    pressupost_extret = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    termini_mesos = models.IntegerField(null=True, blank=True)
    data_limit = models.DateField(null=True, blank=True)
    formula_economica = models.TextField(blank=True)
    classificacio_completa = models.CharField(max_length=20, blank=True)
    requereix_declaracio = models.BooleanField(null=True)

    # Resum generat pel LLM
    resum_executiu = models.TextField(blank=True)

    # Referència MongoDB (on es guarden les dades completes + raw LLM response)
    mongo_extraccion_id = models.CharField(max_length=50, blank=True)

    # Metadades
    model_usat = models.CharField(max_length=100, blank=True)
    prompt_versio = models.CharField(max_length=20, default='v1')
    intents = models.PositiveSmallIntegerField(default=0)
    error_msg = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualitzada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Extracció IA'
        verbose_name_plural = 'Extraccions IA'

    def __str__(self):
        return f'Extracció #{self.pk} — {self.licitacio.expediente_id} [{self.estat}]'
