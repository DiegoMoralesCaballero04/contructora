from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Organismo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=500)),
                ('nif', models.CharField(blank=True, max_length=20)),
                ('provincia', models.CharField(blank=True, max_length=100)),
                ('municipio', models.CharField(blank=True, max_length=200)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Organisme', 'verbose_name_plural': 'Organismes', 'ordering': ['nombre']},
        ),
        migrations.CreateModel(
            name='Licitacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('expediente_id', models.CharField(db_index=True, max_length=200, unique=True)),
                ('url_origen', models.URLField(max_length=1000)),
                ('titulo', models.CharField(max_length=1000)),
                ('provincia', models.CharField(blank=True, max_length=100)),
                ('municipio', models.CharField(blank=True, max_length=200)),
                ('importe_base', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('importe_iva', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('procedimiento', models.CharField(choices=[('ABIERTO', 'Obert'), ('RESTRINGIDO', 'Restringit'), ('NEGOCIADO', 'Negociat'), ('SIMPLIFICADO', 'Simplificat'), ('OTRO', 'Altre')], default='ABIERTO', max_length=20)),
                ('fecha_publicacion', models.DateField(blank=True, null=True)),
                ('fecha_limite_oferta', models.DateTimeField(blank=True, null=True)),
                ('plazo_ejecucion_dias', models.IntegerField(blank=True, null=True)),
                ('clasificacion_grupo', models.CharField(blank=True, max_length=5)),
                ('clasificacion_subgrupo', models.CharField(blank=True, max_length=5)),
                ('clasificacion_categoria', models.CharField(blank=True, max_length=5)),
                ('pdf_pliego_s3_key', models.CharField(blank=True, max_length=500)),
                ('pdf_pliego_url', models.URLField(blank=True, max_length=1000)),
                ('pdf_descargado', models.BooleanField(default=False)),
                ('estado', models.CharField(choices=[('NUEVA', 'Nova'), ('REVISADA', 'Revisada'), ('DESCARTADA', 'Descartada'), ('EN_PREPARACION', 'En preparació'), ('PRESENTADA', 'Presentada'), ('ADJUDICADA', 'Adjudicada'), ('DESIERTA', 'Deserta')], db_index=True, default='NUEVA', max_length=20)),
                ('es_relevante', models.BooleanField(default=True)),
                ('notas', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('mongo_id', models.CharField(blank=True, max_length=50)),
                ('organismo', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='licitaciones', to='licitaciones.organismo')),
            ],
            options={'verbose_name': 'Licitació', 'verbose_name_plural': 'Licitacions', 'ordering': ['-fecha_publicacion', '-creado_en']},
        ),
        migrations.CreateModel(
            name='CriterioAdjudicacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=500)),
                ('puntuacion_maxima', models.DecimalField(decimal_places=2, max_digits=6)),
                ('formula', models.TextField(blank=True)),
                ('es_economico', models.BooleanField(default=False)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('licitacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='criterios', to='licitaciones.licitacion')),
            ],
            options={'verbose_name': "Criteri d'adjudicació", 'verbose_name_plural': "Criteris d'adjudicació", 'ordering': ['orden']},
        ),
        migrations.AddIndex(
            model_name='licitacion',
            index=models.Index(fields=['estado', 'provincia'], name='licitacion_estado_provincia_idx'),
        ),
        migrations.AddIndex(
            model_name='licitacion',
            index=models.Index(fields=['fecha_publicacion'], name='licitacion_fecha_pub_idx'),
        ),
        migrations.AddIndex(
            model_name='licitacion',
            index=models.Index(fields=['importe_base'], name='licitacion_importe_idx'),
        ),
    ]
