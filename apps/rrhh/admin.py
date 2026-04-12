from django.contrib import admin
from .models import UserProfile, Fichaje


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'departament', 'telefon', 'actiu', 'data_alta')
    list_filter = ('role', 'actiu', 'departament')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    raw_id_fields = ('user',)


@admin.register(Fichaje)
class FichajeAdmin(admin.ModelAdmin):
    list_display = ('user', 'data', 'entrada', 'sortida', 'hores_treballades', 'tipus')
    list_filter = ('tipus', 'data', 'user')
    search_fields = ('user__username',)
    date_hierarchy = 'data'
