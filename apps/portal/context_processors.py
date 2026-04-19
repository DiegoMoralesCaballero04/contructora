from django.conf import settings


def scraping_context(request):
    has_scraping = False
    try:
        from modules.licitaciones.scraping.models import ScrapingTemplate
        has_scraping = True
    except ImportError:
        pass

    empresa = None
    try:
        from modules.empresa.empresa.models import Empresa
        empresa = Empresa.get()
    except ImportError:
        pass

    return {'has_scraping': has_scraping, 'empresa': empresa}
