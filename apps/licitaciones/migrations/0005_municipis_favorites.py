from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licitaciones', '0004_territoris'),
    ]

    operations = [
        migrations.AddField(
            model_name='configempresa',
            name='municipis_favorites',
            field=models.JSONField(default=list),
        ),
    ]
