from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import datetime


class RolPersonalitzat(models.Model):
    """Custom role with fine-grained permission toggles, manageable from the portal UI."""

    PERMISOS_DISPONIBLES = [
        ('can_see_licitacions',   _('Veure licitaciones')),
        ('can_edit_licitacions',  _('Editar licitaciones')),
        ('can_see_marketing',     _('Veure marketing / prospects')),
        ('can_edit_marketing',    _('Editar marketing / prospects')),
        ('can_see_erp',           _('Veure ERP (factures, albarans, pedidos)')),
        ('can_edit_erp',          _('Editar ERP')),
        ('can_see_rrhh',          _('Veure RRHH / fitxatges')),
        ('can_see_documents',     _('Veure documents')),
        ('can_upload_documents',  _('Pujar documents')),
        ('can_see_rag',           _('Usar IA / RAG')),
        ('can_manage_users',      _('Gestionar usuaris')),
        ('can_manage_roles',      _('Gestionar rols personalitzats')),
        ('can_see_admin',         _('Veure panell d\'administració')),
    ]

    PERMISOS_PER_MODUL = [
        ('licitacions', _('Licitaciones'), [
            'can_see_licitacions', 'can_edit_licitacions',
        ]),
        ('marketing', _('Marketing / CRM'), [
            'can_see_marketing', 'can_edit_marketing',
        ]),
        ('erp', _('ERP'), [
            'can_see_erp', 'can_edit_erp',
        ]),
        ('rrhh', _('RRHH'), [
            'can_see_rrhh',
        ]),
        ('documents', _('Documents'), [
            'can_see_documents', 'can_upload_documents',
        ]),
        ('ia', _('IA / RAG'), [
            'can_see_rag',
        ]),
        ('admin', _('Administració'), [
            'can_manage_users', 'can_manage_roles', 'can_see_admin',
        ]),
    ]

    nom = models.CharField(max_length=100, unique=True, verbose_name=_('Nom del rol'))
    descripcio = models.TextField(blank=True, verbose_name=_('Descripció'))
    permisos = models.JSONField(
        default=dict,
        verbose_name=_('Permisos'),
        help_text='Dict of permission_key: true/false',
    )
    creat_en = models.DateTimeField(auto_now_add=True)
    actualitzat_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Rol personalitzat')
        verbose_name_plural = _('Rols personalitzats')
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def te_permis(self, permis: str) -> bool:
        return bool(self.permisos.get(permis, False))


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
    rol_custom = models.ForeignKey(
        RolPersonalitzat, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_('Rol personalitzat'),
        help_text=_('Si s\'especifica, els permisos es prenen del rol personalitzat.'),
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

    def _permis(self, key: str, default_roles) -> bool:
        if self.rol_custom_id:
            return self.rol_custom.te_permis(key)
        return self.role in default_roles

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN and not self.rol_custom_id

    @property
    def can_see_rrhh(self):
        return self._permis('can_see_rrhh', (self.Role.ADMIN, self.Role.JEFE, self.Role.SUPERVISOR))

    @property
    def can_manage_users(self):
        return self._permis('can_manage_users', (self.Role.ADMIN,))

    @property
    def can_manage_roles(self):
        return self._permis('can_manage_roles', (self.Role.ADMIN,))

    @property
    def can_see_admin(self):
        return self._permis('can_see_admin', (self.Role.ADMIN, self.Role.JEFE, self.Role.SUPERVISOR))

    @property
    def can_see_erp(self):
        return self._permis('can_see_erp', (self.Role.ADMIN, self.Role.JEFE))

    @property
    def can_edit_erp(self):
        return self._permis('can_edit_erp', (self.Role.ADMIN, self.Role.JEFE))

    @property
    def can_see_marketing(self):
        return self._permis('can_see_marketing', (self.Role.ADMIN, self.Role.JEFE, self.Role.SUPERVISOR))

    @property
    def can_see_rag(self):
        return self._permis('can_see_rag', (self.Role.ADMIN, self.Role.JEFE, self.Role.SUPERVISOR))


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
