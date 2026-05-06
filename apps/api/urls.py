from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api.views import ScrapingTriggerView, HealthView

router = DefaultRouter()

try:
    from modules.licitaciones.licitaciones.views import LicitacionViewSet
    router.register('licitacions', LicitacionViewSet, basename='licitacio')
except ImportError:
    pass

try:
    from modules.ofertes.ofertes.views import (
        OfertaViewSet, PressupostViewSet,
        LiniaPressupostViewSet, SolicitudSubcontractistaViewSet,
    )
    router.register('ofertes', OfertaViewSet, basename='oferta')
    router.register('pressupostos', PressupostViewSet, basename='pressupost')
    router.register('linies-pressupost', LiniaPressupostViewSet, basename='linia-pressupost')
    router.register('solicituds-subcontractista', SolicitudSubcontractistaViewSet, basename='solicitud-subcontractista')
except ImportError:
    pass

try:
    from modules.calendari.calendari.views import EsdevenimentViewSet
    router.register('esdeveniments', EsdevenimentViewSet, basename='esdeveniment')
except ImportError:
    pass

try:
    from modules.marketing.marketing.views import (
        EmpresaProspectViewSet, CampanyaMarketingViewSet, PlantillaEmailViewSet,
    )
    router.register('prospects', EmpresaProspectViewSet, basename='prospect')
    router.register('campanyes', CampanyaMarketingViewSet, basename='campanya')
    router.register('plantilles-email', PlantillaEmailViewSet, basename='plantilla-email')
except ImportError:
    pass

try:
    from modules.documents.documents.views import DocumentViewSet
    router.register('documents', DocumentViewSet, basename='document')
except ImportError:
    pass

try:
    from modules.rag.rag.views import ConsultaRAGViewSet
    router.register('rag/historial', ConsultaRAGViewSet, basename='consulta-rag')
except ImportError:
    pass

urlpatterns = [
    path('', include(router.urls)),
    path('scraping/executar/', ScrapingTriggerView.as_view(), name='scraping-trigger'),
    path('health/', HealthView.as_view(), name='health'),
]

try:
    from modules.empresa.empresa.views import EmpresaView
    urlpatterns += [
        path('empresa/', EmpresaView.as_view(), name='empresa'),
    ]
except ImportError:
    pass

try:
    from modules.calendari.calendari.views import (
        CalendariConfigView, MicrosoftOAuthInitView, MicrosoftOAuthCallbackView,
    )
    urlpatterns += [
        path('calendari/config/', CalendariConfigView.as_view(), name='calendari-config'),
        path('calendari/oauth/init/', MicrosoftOAuthInitView.as_view(), name='calendari-oauth-init'),
        path('calendari/oauth/callback/', MicrosoftOAuthCallbackView.as_view(), name='calendari-oauth-callback'),
    ]
except ImportError:
    pass

try:
    from modules.marketing.marketing.views import UnsubscribeView, TrackingOpenView
    urlpatterns += [
        path('marketing/baixa/<uuid:token>/', UnsubscribeView.as_view(), name='marketing-baixa'),
        path('marketing/track/<uuid:token>/open.gif', TrackingOpenView.as_view(), name='marketing-track-open'),
    ]
except ImportError:
    pass

try:
    from modules.rag.rag.views import ConsultaRAGView
    urlpatterns += [
        path('rag/consulta/', ConsultaRAGView.as_view(), name='rag-consulta'),
    ]
except ImportError:
    pass
