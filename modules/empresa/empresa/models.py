from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class Empresa(models.Model):
    nombre_empresa = models.CharField(max_length=200, verbose_name=_('Nombre empresa'))
    direccion = models.CharField(max_length=500, blank=True, verbose_name=_('Dirección'))
    ciudad = models.CharField(max_length=100, blank=True, verbose_name=_('Ciudad'))
    pais = models.CharField(max_length=100, default='España', verbose_name=_('País'))
    email_contacto = models.EmailField(blank=True, verbose_name=_('Email de contacto'))
    telefono = models.CharField(max_length=30, blank=True, verbose_name=_('Teléfono'))
    logo = models.ImageField(
        upload_to='empresa/logos/', blank=True, null=True, verbose_name=_('Logo')
    )
    descripcion = models.TextField(blank=True, verbose_name=_('Descripción'))
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresa'

    def __str__(self):
        return self.nombre_empresa

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('El registro de empresa no puede eliminarse.')

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'nombre_empresa': 'Mi Empresa'})
        return obj
