from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rrhh', '0002_alter_fichaje_id_alter_fichaje_tipus_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RolPersonalitzat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100, unique=True, verbose_name='Nom del rol')),
                ('descripcio', models.TextField(blank=True, verbose_name='Descripció')),
                ('permisos', models.JSONField(default=dict, help_text='Dict of permission_key: true/false', verbose_name='Permisos')),
                ('creat_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Rol personalitzat',
                'verbose_name_plural': 'Rols personalitzats',
                'ordering': ['nom'],
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='rol_custom',
            field=models.ForeignKey(
                blank=True,
                help_text="Si s'especifica, els permisos es prenen del rol personalitzat.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='rrhh.rolpersonalitzat',
                verbose_name='Rol personalitzat',
            ),
        ),
    ]
