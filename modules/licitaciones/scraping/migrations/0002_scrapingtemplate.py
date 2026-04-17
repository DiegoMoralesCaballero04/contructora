import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraping', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapingTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200)),
                ('activa', models.BooleanField(db_index=True, default=True)),
                ('importe_min', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('importe_max', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('provincies', models.JSONField(blank=True, default=list)),
                ('tipus_contracte', models.JSONField(blank=True, default=list)),
                ('procediments', models.JSONField(blank=True, default=list)),
                ('cpv_inclosos', models.JSONField(blank=True, default=list)),
                ('max_pagines', models.IntegerField(default=10)),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzada_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Plantilla de scraping',
                'verbose_name_plural': 'Plantilles de scraping',
                'ordering': ['nom'],
            },
        ),
        migrations.AddField(
            model_name='scrapingjob',
            name='template',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='jobs',
                to='scraping.scrapingtemplate',
            ),
        ),
    ]
