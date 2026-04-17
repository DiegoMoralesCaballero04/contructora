from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraping', '0003_singleton_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='scrapingtemplate',
            name='municipis',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
