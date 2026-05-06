from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('', RedirectView.as_view(url='/portal/', permanent=False)),
    path('admin/', admin.site.urls),
    path('portal/', include('apps.portal.urls')),
    path('api/v1/', include('apps.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'CONSTRUTECH-IA'
admin.site.site_title = 'CONSTRUTECH-IA Admin'
admin.site.index_title = 'Gestió de Licitacions'
