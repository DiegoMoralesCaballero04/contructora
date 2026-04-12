from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = [('licitaciones', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='Extraccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estat', models.CharField(choices=[('PENDENT', 'Pendent'), ('EN_CURS', 'En curs'), ('OK', 'Correcte'), ('ERROR', 'Error'), ('REVISAR', 'Cal revisar')], default='PENDENT', max_length=10)),
                ('objecte_extret', models.TextField(blank=True)),
                ('pressupost_extret', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('termini_mesos', models.IntegerField(blank=True, null=True)),
                ('data_limit', models.DateField(blank=True, null=True)),
                ('formula_economica', models.TextField(blank=True)),
                ('classificacio_completa', models.CharField(blank=True, max_length=20)),
                ('requereix_declaracio', models.BooleanField(null=True)),
                ('resum_executiu', models.TextField(blank=True)),
                ('mongo_extraccion_id', models.CharField(blank=True, max_length=50)),
                ('model_usat', models.CharField(blank=True, max_length=100)),
                ('prompt_versio', models.CharField(default='v1', max_length=20)),
                ('intents', models.PositiveSmallIntegerField(default=0)),
                ('error_msg', models.TextField(blank=True)),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzada_en', models.DateTimeField(auto_now=True)),
                ('licitacio', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='extraccion', to='licitaciones.licitacion')),
            ],
            options={'verbose_name': 'Extracció IA', 'verbose_name_plural': 'Extraccions IA'},
        ),
    ]
