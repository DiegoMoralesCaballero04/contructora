from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ScrapingJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('iniciat_en', models.DateTimeField(auto_now_add=True)),
                ('finalitzat_en', models.DateTimeField(blank=True, null=True)),
                ('estat', models.CharField(choices=[('PENDENT', 'Pendent'), ('EN_CURS', 'En curs'), ('COMPLETAT', 'Completat'), ('ERROR', 'Error')], default='PENDENT', max_length=20)),
                ('total_trobades', models.IntegerField(default=0)),
                ('noves_insertades', models.IntegerField(default=0)),
                ('actualitzades', models.IntegerField(default=0)),
                ('descartades', models.IntegerField(default=0)),
                ('errors', models.IntegerField(default=0)),
                ('detalls_error', models.TextField(blank=True)),
                ('filtres_aplicats', models.JSONField(default=dict)),
            ],
            options={'verbose_name': 'Treball de scraping', 'verbose_name_plural': 'Treballs de scraping', 'ordering': ['-iniciat_en']},
        ),
    ]
