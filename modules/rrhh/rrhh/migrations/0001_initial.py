from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('role', models.CharField(
                    choices=[('ADMIN','Administrador'),('JEFE','Cap'),('SUPERVISOR','Supervisor'),('TRABAJADOR','Treballador')],
                    db_index=True, default='TRABAJADOR', max_length=20
                )),
                ('telefon', models.CharField(blank=True, max_length=20)),
                ('departament', models.CharField(blank=True, max_length=100)),
                ('data_alta', models.DateField(blank=True, null=True)),
                ('actiu', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile', to=settings.AUTH_USER_MODEL
                )),
            ],
            options={'verbose_name': "Perfil d'usuari", 'verbose_name_plural': "Perfils d'usuari"},
        ),
        migrations.CreateModel(
            name='Fichaje',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('data', models.DateField(db_index=True)),
                ('entrada', models.DateTimeField(blank=True, null=True)),
                ('sortida', models.DateTimeField(blank=True, null=True)),
                ('tipus', models.CharField(
                    choices=[('NORMAL','Normal'),('TELETREBALL','Teletreball'),('GUARDIA','Guàrdia')],
                    default='NORMAL', max_length=20
                )),
                ('notes', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='fichajes', to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Fitxatge',
                'verbose_name_plural': 'Fitxatges',
                'ordering': ['-data', '-entrada'],
                'unique_together': {('user', 'data')},
            },
        ),
    ]
