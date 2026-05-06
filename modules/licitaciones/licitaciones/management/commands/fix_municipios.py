"""
Management command to clean up incorrect municipio values.

The scraper was storing the contracting organism's city (often 'Madrid' for
national bodies) instead of the actual execution location. This command clears
those misleading values.

Usage:
    python manage.py fix_municipios           # dry run (shows what would change)
    python manage.py fix_municipios --apply   # apply the fix
"""
from django.core.management.base import BaseCommand
from modules.licitaciones.licitaciones.models import Licitacion

MADRID_REGIONS = {'madrid', 'comunidad de madrid', 'madrid (comunidad de)'}


class Command(BaseCommand):
    help = 'Clear municipio="Madrid" when the provincia is not a Madrid region'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply the fix (default is dry run)',
        )

    def handle(self, *args, **options):
        apply = options['apply']

        # Find licitaciones where municipio is Madrid but provincia is not
        qs = Licitacion.objects.filter(municipio__iexact='madrid').exclude(
            provincia__icontains='madrid'
        )

        count = qs.count()
        self.stdout.write(f'Found {count} licitaciones with municipio=Madrid and non-Madrid provincia.')

        if count == 0:
            self.stdout.write(self.style.SUCCESS('Nothing to fix.'))
            return

        if not apply:
            self.stdout.write('Dry run — pass --apply to make changes. Sample:')
            for l in qs[:10]:
                self.stdout.write(f'  [{l.expediente_id}] municipio={l.municipio!r} provincia={l.provincia!r}')
            return

        updated = qs.update(municipio='')
        self.stdout.write(self.style.SUCCESS(
            f'Fixed {updated} licitaciones: municipio cleared where it was wrong.'
        ))
