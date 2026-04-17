from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api.views import ScrapingTriggerView, HealthView

router = DefaultRouter()

try:
    from modules.licitaciones.licitaciones.views import LicitacionViewSet
    router.register('licitacions', LicitacionViewSet, basename='licitacio')
except ImportError:
    pass

urlpatterns = [
    path('', include(router.urls)),
    path('scraping/executar/', ScrapingTriggerView.as_view(), name='scraping-trigger'),
    path('health/', HealthView.as_view(), name='health'),
]
