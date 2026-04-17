"""
Script d'inicialització de rols i perfils d'usuari.

Execució:
    docker compose exec django python scripts/init_roles.py
    # o fora de Docker:
    python scripts/init_roles.py
"""
import os
import sys
import django

# Afegim el directori arrel al path i configurem Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth.models import User
from modules.rrhh.rrhh.models import UserProfile


def init_roles():
    users = User.objects.all()
    creats = 0
    actualitzats = 0

    for user in users:
        profile, created = UserProfile.objects.get_or_create(user=user)

        if created:
            creats += 1

        # El superusuari (is_superuser=True) sempre és ADMIN
        if user.is_superuser and profile.role != UserProfile.Role.ADMIN:
            profile.role = UserProfile.Role.ADMIN
            profile.save(update_fields=['role'])
            actualitzats += 1
            print(f"  [ADMIN]  {user.username} (superusuari → ADMIN)")
        elif created:
            print(f"  [NOU]    {user.username} → {profile.get_role_display()}")
        else:
            print(f"  [OK]     {user.username} → {profile.get_role_display()}")

    print(f"\nFet: {creats} perfils creats, {actualitzats} rols actualitzats.")
    print(f"Total usuaris: {users.count()}")


if __name__ == '__main__':
    print("=== Inicialitzant rols i perfils d'usuari ===\n")
    init_roles()
