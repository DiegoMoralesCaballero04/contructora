from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licitaciones', '0003_informeintern_pdf_s3'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigEmpresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provincia_principal', models.CharField(blank=True, max_length=100)),
                ('provincies_favorites', models.JSONField(default=list)),
            ],
            options={
                'verbose_name': 'Configuració empresa',
            },
        ),
        migrations.CreateModel(
            name='ContacteProvincial',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provincia', models.CharField(db_index=True, max_length=100)),
                ('nom', models.CharField(max_length=200)),
                ('empresa', models.CharField(blank=True, max_length=200)),
                ('rol', models.CharField(
                    choices=[
                        ('SUBCONTRACTISTA', 'Subcontractista'),
                        ('PROVEIDOR', 'Proveïdor'),
                        ('DELEGAT', 'Delegat local'),
                        ('TECNIC', 'Tècnic / Arquitecte'),
                        ('ALTRE', 'Altre'),
                    ],
                    default='ALTRE',
                    max_length=20,
                )),
                ('telefon', models.CharField(blank=True, max_length=30)),
                ('email', models.EmailField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Contacte provincial',
                'verbose_name_plural': 'Contactes provincials',
                'ordering': ['provincia', 'nom'],
            },
        ),
    ]
