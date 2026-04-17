from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import datetime


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN      = 'ADMIN',      _('Administrador')
        JEFE       = 'JEFE',       _('Jefe')
        SUPERVISOR = 'SUPERVISOR', _('Supervisor')
        TRABAJADOR = 'TRABAJADOR', _('Trabajador')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.TRABAJADOR, db_index=True
    )
    telefon = models.CharField(max_length=20, blank=True)
    departament = models.CharField(max_length=100, blank=True)
    data_alta = models.DateField(null=True, blank=True)
    actiu = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Perfil d\'usuari'
        verbose_name_plural = 'Perfils d\'usuari'

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} [{self.get_role_display()}]'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def can_see_rrhh(self):
        return self.role in (self.Role.ADMIN, self.Role.JEFE, self.Role.SUPERVISOR)

    @property
    def can_manage_users(self):
        return self.role == self.Role.ADMIN


class Fichaje(models.Model):
    class Tipus(models.TextChoices):
        NORMAL      = 'NORMAL',      _('Normal')
        TELETREBALL = 'TELETREBALL', _('Teletrabajo')
        GUARDIA     = 'GUARDIA',     _('Guardia')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fichajes')
    data = models.DateField(db_index=True)
    entrada = models.DateTimeField(null=True, blank=True)
    sortida = models.DateTimeField(null=True, blank=True)
    tipus = models.CharField(max_length=20, choices=Tipus.choices, default=Tipus.NORMAL)
    notes = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fitxatge'
        verbose_name_plural = 'Fitxatges'
        ordering = ['-data', '-entrada']
        unique_together = [('user', 'data')]

    def __str__(self):
        return f'{self.user.username} — {self.data}'

    @property
    def hores_treballades(self) -> float | None:
        if self.entrada and self.sortida:
            delta = self.sortida - self.entrada
            return round(delta.total_seconds() / 3600, 2)
        return None

    @property
    def en_curs(self) -> bool:
        return self.entrada is not None and self.sortida is None
