from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.rrhh.models import UserProfile


class Command(BaseCommand):
    help = 'Creates UserProfile for all users and sets superusers as ADMIN'

    def handle(self, *args, **options):
        users = User.objects.all()
        creats = 0
        actualitzats = 0

        for user in users:
            profile, created = UserProfile.objects.get_or_create(user=user)

            if created:
                creats += 1

            if user.is_superuser and profile.role != UserProfile.Role.ADMIN:
                profile.role = UserProfile.Role.ADMIN
                profile.save(update_fields=['role'])
                actualitzats += 1
                self.stdout.write(f'  [ADMIN]  {user.username} (superusuari → ADMIN)')
            elif created:
                self.stdout.write(f'  [NOU]    {user.username} → {profile.get_role_display()}')
            else:
                self.stdout.write(f'  [OK]     {user.username} → {profile.get_role_display()}')

        self.stdout.write(self.style.SUCCESS(
            f'\nFet: {creats} perfils creats, {actualitzats} rols actualitzats. Total: {users.count()} usuaris.'
        ))
