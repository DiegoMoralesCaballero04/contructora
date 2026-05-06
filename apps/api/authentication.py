from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from django.contrib.auth.models import User


class ApiKeyAuthentication(BaseAuthentication):
    """Simple API key authentication for n8n service account integration."""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY') or request.GET.get('api_key')
        if not api_key:
            return None

        expected = getattr(settings, 'API_KEY', '')
        if not expected or api_key != expected:
            raise AuthenticationFailed('Invalid API key')

        # Return a system user for n8n service calls
        user, _ = User.objects.get_or_create(
            username='n8n-service',
            defaults={'is_staff': False, 'is_active': True},
        )
        return (user, api_key)
