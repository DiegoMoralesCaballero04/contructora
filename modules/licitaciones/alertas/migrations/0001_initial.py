from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='AlertaConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activa', models.BooleanField(default=True)),
                ('email_actiu', models.BooleanField(default=True)),
                ('telegram_actiu', models.BooleanField(default=False)),
                ('importe_max', models.DecimalField(decimal_places=2, default=4000000, max_digits=14)),
                ('provincies', models.JSONField(default=list)),
                ('procediments', models.JSONField(default=list)),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('usuari', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='alerta_config', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': "Configuració d'alerta", 'verbose_name_plural': "Configuracions d'alerta"},
        ),
    ]
