from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Empresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_empresa', models.CharField(max_length=200, verbose_name='Nombre empresa')),
                ('direccion', models.CharField(blank=True, max_length=500, verbose_name='Dirección')),
                ('ciudad', models.CharField(blank=True, max_length=100, verbose_name='Ciudad')),
                ('pais', models.CharField(default='España', max_length=100, verbose_name='País')),
                ('email_contacto', models.EmailField(blank=True, max_length=254, verbose_name='Email de contacto')),
                ('telefono', models.CharField(blank=True, max_length=30, verbose_name='Teléfono')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='empresa/logos/', verbose_name='Logo')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Empresa',
                'verbose_name_plural': 'Empresa',
            },
        ),
    ]
