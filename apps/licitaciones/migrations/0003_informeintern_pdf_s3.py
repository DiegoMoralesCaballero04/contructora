from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licitaciones', '0002_informeintern'),
    ]

    operations = [
        migrations.AddField(
            model_name='informeintern',
            name='pdf_s3_key',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='informeintern',
            name='pdf_s3_url',
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
