from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=300, verbose_name='Nom / Raó social')),
                ('nif', models.CharField(blank=True, max_length=20, verbose_name='NIF / CIF')),
                ('email', models.EmailField(blank=True)),
                ('telefon', models.CharField(blank=True, max_length=30)),
                ('adreca', models.CharField(blank=True, max_length=300, verbose_name='Adreça')),
                ('poblacio', models.CharField(blank=True, max_length=100, verbose_name='Població')),
                ('codi_postal', models.CharField(blank=True, max_length=10)),
                ('provincia', models.CharField(blank=True, max_length=100, verbose_name='Província')),
                ('pais', models.CharField(default='España', max_length=100, verbose_name='País')),
                ('actiu', models.BooleanField(default=True, verbose_name='Actiu')),
                ('notes', models.TextField(blank=True)),
                ('creat_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_en', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Client', 'verbose_name_plural': 'Clients', 'ordering': ['nom']},
        ),
        migrations.CreateModel(
            name='Pedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(max_length=50, unique=True, verbose_name='Número')),
                ('estat', models.CharField(choices=[('ESBORRANY', 'Esborrany'), ('CONFIRMAT', 'Confirmat'), ('EN_CURS', 'En curs'), ('COMPLETAT', 'Completat'), ('CANCEL_LAT', 'Cancel·lat')], db_index=True, default='ESBORRANY', max_length=20)),
                ('data', models.DateField(default=django.utils.timezone.localdate, verbose_name='Data')),
                ('data_entrega', models.DateField(blank=True, null=True, verbose_name="Data d'entrega")),
                ('referencia_client', models.CharField(blank=True, max_length=100, verbose_name='Ref. client')),
                ('notes', models.TextField(blank=True)),
                ('creat_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_en', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pedidos', to='erp.client')),
                ('creat_per', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos_creats', to='auth.user')),
            ],
            options={'verbose_name': 'Pedido', 'verbose_name_plural': 'Pedidos', 'ordering': ['-data', '-creat_en']},
        ),
        migrations.CreateModel(
            name='LiniaPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcio', models.CharField(max_length=500, verbose_name='Descripció')),
                ('quantitat', models.DecimalField(decimal_places=3, default=Decimal('1'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))])),
                ('preu_unitari', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Preu unitari')),
                ('descompte', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=5, verbose_name='Descompte %')),
                ('iva', models.DecimalField(choices=[(Decimal('0.00'), '0 %'), (Decimal('4.00'), '4 %'), (Decimal('10.00'), '10 %'), (Decimal('21.00'), '21 %')], decimal_places=2, default=Decimal('21.00'), max_digits=5, verbose_name='IVA %')),
                ('ordre', models.PositiveSmallIntegerField(default=0)),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linies', to='erp.pedido')),
            ],
            options={'ordering': ['ordre', 'id']},
        ),
        migrations.CreateModel(
            name='Albara',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(max_length=50, unique=True, verbose_name='Número')),
                ('estat', models.CharField(choices=[('ESBORRANY', 'Esborrany'), ('EMÈS', 'Emès'), ('FACTURAT', 'Facturat')], db_index=True, default='ESBORRANY', max_length=20)),
                ('data', models.DateField(default=django.utils.timezone.localdate, verbose_name='Data')),
                ('notes', models.TextField(blank=True)),
                ('creat_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_en', models.DateTimeField(auto_now=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='albarans', to='erp.client')),
                ('pedido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='albarans', to='erp.pedido')),
                ('creat_per', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='albarans_creats', to='auth.user')),
            ],
            options={'verbose_name': 'Albarà', 'verbose_name_plural': 'Albarans', 'ordering': ['-data', '-creat_en']},
        ),
        migrations.CreateModel(
            name='LiniaAlbara',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcio', models.CharField(max_length=500, verbose_name='Descripció')),
                ('quantitat', models.DecimalField(decimal_places=3, default=Decimal('1'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))])),
                ('preu_unitari', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Preu unitari')),
                ('ordre', models.PositiveSmallIntegerField(default=0)),
                ('albara', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linies', to='erp.albara')),
            ],
            options={'ordering': ['ordre', 'id']},
        ),
        migrations.CreateModel(
            name='Factura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serie', models.CharField(default='F', max_length=10, verbose_name='Sèrie')),
                ('numero', models.PositiveIntegerField(verbose_name='Número')),
                ('numero_complet', models.CharField(editable=False, max_length=50, unique=True, verbose_name='Número complet')),
                ('tipus', models.CharField(choices=[('ORDINARIA', 'Ordinària'), ('RECTIFICATIVA', 'Rectificativa'), ('PROFORMA', 'Proforma')], default='ORDINARIA', max_length=20)),
                ('estat', models.CharField(choices=[('ESBORRANY', 'Esborrany'), ('EMESA', 'Emesa'), ('COBRADA', 'Cobrada'), ('VENÇUDA', 'Vençuda'), ('ANUL_LADA', 'Anul·lada')], db_index=True, default='ESBORRANY', max_length=20)),
                ('data_emisio', models.DateField(default=django.utils.timezone.localdate, verbose_name='Data emissió')),
                ('data_venciment', models.DateField(blank=True, null=True, verbose_name='Data venciment')),
                ('base_imponible', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=14, verbose_name='Base imposable')),
                ('total_iva', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=14, verbose_name='Total IVA')),
                ('total_irpf', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=14, verbose_name='Retenció IRPF')),
                ('total', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=14, verbose_name='Total')),
                ('irpf_percentatge', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=5, verbose_name='IRPF %')),
                ('notes', models.TextField(blank=True)),
                ('notes_internes', models.TextField(blank=True)),
                ('verifactu', models.BooleanField(default=False, help_text="Enviar al sistema de verificació de factures de l'AEAT (Reial Decret 1007/2023)", verbose_name='Enviar a VerifactuRE')),
                ('verifactu_enviat_en', models.DateTimeField(blank=True, editable=False, null=True)),
                ('verifactu_hash', models.CharField(blank=True, editable=False, max_length=64)),
                ('creat_en', models.DateTimeField(auto_now_add=True)),
                ('actualitzat_en', models.DateTimeField(auto_now=True)),
                ('albara', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='factures', to='erp.albara')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='factures', to='erp.client')),
                ('pedido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='factures', to='erp.pedido')),
                ('creat_per', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='factures_creades', to='auth.user')),
                ('factura_rectificada', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rectificatives', to='erp.factura', verbose_name='Factura rectificada')),
            ],
            options={'verbose_name': 'Factura', 'verbose_name_plural': 'Factures', 'ordering': ['-data_emisio', '-numero']},
        ),
        migrations.AddConstraint(
            model_name='factura',
            constraint=models.UniqueConstraint(fields=['serie', 'numero'], name='unique_serie_numero'),
        ),
        migrations.CreateModel(
            name='LiniaFactura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcio', models.CharField(max_length=500, verbose_name='Descripció')),
                ('quantitat', models.DecimalField(decimal_places=3, default=Decimal('1'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))])),
                ('preu_unitari', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Preu unitari')),
                ('descompte', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=5, verbose_name='Descompte %')),
                ('iva', models.DecimalField(choices=[(Decimal('0.00'), '0 %'), (Decimal('4.00'), '4 %'), (Decimal('10.00'), '10 %'), (Decimal('21.00'), '21 %')], decimal_places=2, default=Decimal('21.00'), max_digits=5, verbose_name='IVA %')),
                ('ordre', models.PositiveSmallIntegerField(default=0)),
                ('factura', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linies', to='erp.factura')),
            ],
            options={'ordering': ['ordre', 'id']},
        ),
    ]
