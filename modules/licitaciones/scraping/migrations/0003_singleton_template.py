from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraping', '0002_scrapingtemplate'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='scrapingtemplate',
            constraint=models.CheckConstraint(check=models.Q(pk=1), name='only_one_template'),
        ),
    ]
