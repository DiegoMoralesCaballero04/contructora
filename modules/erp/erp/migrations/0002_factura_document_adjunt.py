from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('erp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='factura',
            name='document_adjunt',
            field=models.FileField(blank=True, null=True, upload_to='erp/factures/%Y/%m/', verbose_name='Document adjunt (PDF/imatge)'),
        ),
        migrations.AddField(
            model_name='factura',
            name='extraccio_ia',
            field=models.JSONField(blank=True, default=dict, verbose_name='Dades extretes per IA'),
        ),
    ]
