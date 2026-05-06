from django.db import migrations

CATEGORIES = [
    ('ISO-Q',       'ISO 9001 — Qualitat',        'Sistema de gestió de qualitat',             10, True,  10, None),
    ('ISO-Q-PROC',  'Procediments',                'Procediments del sistema de qualitat',      10, True,  11, 'ISO-Q'),
    ('ISO-Q-REG',   'Registres qualitat',           'Registres i evidències de qualitat',        10, False, 12, 'ISO-Q'),
    ('ISO-Q-MAN',   'Manual de qualitat',           'Manual del sistema de gestió de qualitat',  10, True,  13, 'ISO-Q'),
    ('ISO-MA',      'ISO 14001 — Medi ambient',    'Sistema de gestió mediambiental',           10, True,  20, None),
    ('ISO-MA-PLAN', 'Plans mediambientals',         'Plans i programes mediambientals',          10, True,  21, 'ISO-MA'),
    ('ISO-MA-REG',  'Registres medi ambient',       'Registres i evidències mediambientals',     10, False, 22, 'ISO-MA'),
    ('LICIT',       'Licitacions',                  'Documents de licitacions públiques',         5, False, 30, None),
    ('LICIT-PLEC',  'Plecs de condicions',          'Plecs de clàusules administratives i tècniques', 5, False, 31, 'LICIT'),
    ('LICIT-OFERT', 'Ofertes presentades',          'Propostes econòmiques i tècniques',          5, False, 32, 'LICIT'),
    ('LICIT-CONT',  'Contractes adjudicats',        'Contractes signats i adjudicats',            7, True,  33, 'LICIT'),
    ('RRHH',        'Recursos Humans',              'Documents de gestió del personal',           7, True,  40, None),
    ('RRHH-CONT',   'Contractes laborals',          'Contractes de treball del personal',         7, True,  41, 'RRHH'),
    ('RRHH-FORM',   'Formació i certificats',       'Certificats i materials de formació',        5, False, 42, 'RRHH'),
    ('RRHH-PRL',    'Prevenció de riscos',          'Documents PRL i seguretat laboral',         10, True,  43, 'RRHH'),
    ('GENERAL',     'Documents generals',           "Altres documents de l'empresa",              5, False, 50, None),
    ('GEN-FACT',    'Factures',                     'Factures i rebuts',                          7, False, 51, 'GENERAL'),
    ('GEN-CORR',    'Correspondència',              'Correspondència comercial i administrativa',  3, False, 52, 'GENERAL'),
    ('GEN-PROJ',    'Projectes tècnics',            'Projectes, plànols i memòries tècniques',   10, False, 53, 'GENERAL'),
]


def crear_categories(apps, schema_editor):
    CategoriaDocument = apps.get_model('documents', 'CategoriaDocument')
    if CategoriaDocument.objects.exists():
        return

    created = {}
    for codi, nom, desc, ret, aprov, ordre, pare_codi in CATEGORIES:
        pare = created.get(pare_codi) if pare_codi else None
        cat = CategoriaDocument.objects.create(
            codi=codi, nom=nom, descripcio=desc,
            retencio_anys=ret, requereix_aprovacio=aprov,
            ordre=ordre, pare=pare,
        )
        created[codi] = cat


def eliminar_categories(apps, schema_editor):
    CategoriaDocument = apps.get_model('documents', 'CategoriaDocument')
    CategoriaDocument.objects.filter(
        codi__in=[c[0] for c in CATEGORIES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('documents', '0002_initial'),
    ]
    operations = [
        migrations.RunPython(crear_categories, eliminar_categories),
    ]
