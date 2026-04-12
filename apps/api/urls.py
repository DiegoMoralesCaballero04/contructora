from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.licitaciones.views import LicitacionViewSet
from apps.api.views import ScrapingTriggerView, HealthView

router = DefaultRouter()
router.register('licitacions', LicitacionViewSet, basename='licitacio')

urlpatterns = [
    path('', include(router.urls)),
    path('scraping/executar/', ScrapingTriggerView.as_view(), name='scraping-trigger'),
    path('health/', HealthView.as_view(), name='health'),
]
