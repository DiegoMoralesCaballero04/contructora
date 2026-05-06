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

    profile = None
    if request.user.is_authenticated:
        try:
            from modules.rrhh.rrhh.models import UserProfile
            profile = UserProfile.objects.filter(user=request.user).first()
        except ImportError:
            pass

    return {'has_scraping': has_scraping, 'empresa': empresa, 'profile': profile}
