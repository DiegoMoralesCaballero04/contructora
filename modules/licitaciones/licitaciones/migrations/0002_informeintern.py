from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('licitaciones', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InformeIntern',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recomendacio', models.CharField(
                    choices=[('PRESENTAR', 'Presentar oferta'), ('DESCARTAR', 'Descartar'), ('ESTUDIAR', 'Estudiar més')],
                    default='ESTUDIAR', max_length=20,
                )),
                ('puntuacio', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('analisi_tecnica', models.TextField(blank=True)),
                ('punts_forts', models.TextField(blank=True)),
                ('punts_febles', models.TextField(blank=True)),
                ('observacions', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('autor', models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='informes', to=settings.AUTH_USER_MODEL,
                )),
                ('licitacion', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='informes', to='licitaciones.licitacion',
                )),
            ],
            options={
                'verbose_name': 'Informe intern',
                'verbose_name_plural': 'Informes interns',
                'ordering': ['-creado_en'],
            },
        ),
    ]
