from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('action', models.CharField(
                    choices=[
                        ('CREATE', 'Creació'), ('UPDATE', 'Actualització'), ('DELETE', 'Eliminació'),
                        ('LOGIN', 'Inici de sessió'), ('LOGOUT', 'Tancament de sessió'),
                        ('SCRAPING', 'Scraping executat'), ('EXTRACCION', 'Extracció IA'),
                        ('S3_UPLOAD', 'Pujada S3'), ('S3_DOWNLOAD', 'Descàrrega S3'),
                        ('ALERT_SENT', 'Alerta enviada'), ('API_CALL', 'Crida API'),
                    ],
                    db_index=True, max_length=20
                )),
                ('model_name', models.CharField(blank=True, db_index=True, max_length=100)),
                ('object_id', models.CharField(blank=True, max_length=200)),
                ('object_repr', models.CharField(blank=True, max_length=500)),
                ('changes', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('extra', models.JSONField(blank=True, default=dict)),
                ('user', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs', to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': "Registre d'auditoria",
                'verbose_name_plural': "Registres d'auditoria",
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'timestamp'], name='audit_action_ts_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['model_name', 'object_id'], name='audit_model_obj_idx'),
        ),
    ]
