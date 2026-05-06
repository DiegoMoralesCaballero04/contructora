import logging
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Esdeveniment, CalendariConfig
from .serializers import EsdevenimentSerializer, CalendariConfigSerializer

logger = logging.getLogger(__name__)


class EsdevenimentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EsdevenimentSerializer

    def get_queryset(self):
        qs = Esdeveniment.objects.select_related(
            'licitacio', 'oferta', 'creador'
        ).prefetch_related('assistents')

        from_date = self.request.query_params.get('from')
        to_date = self.request.query_params.get('to')
        if from_date:
            qs = qs.filter(inici__date__gte=from_date)
        if to_date:
            qs = qs.filter(inici__date__lte=to_date)

        tipus = self.request.query_params.get('tipus')
        if tipus:
            qs = qs.filter(tipus=tipus)

        return qs.order_by('inici')

    def perform_create(self, serializer):
        esdev = serializer.save(creador=self.request.user)
        from .tasks import sincronitzar_esdeveniment
        sincronitzar_esdeveniment.delay(esdev.pk)

    def perform_update(self, serializer):
        esdev = serializer.save()
        from .tasks import sincronitzar_esdeveniment
        sincronitzar_esdeveniment.delay(esdev.pk)

    @action(detail=True, methods=['post'], url_path='sincronitzar')
    def sincronitzar(self, request, pk=None):
        from .tasks import sincronitzar_esdeveniment
        esdev = self.get_object()
        sincronitzar_esdeveniment.delay(esdev.pk)
        return Response({'status': 'sincronitzant', 'id': esdev.pk})


class CalendariConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        config, _ = CalendariConfig.objects.get_or_create(usuari=request.user)
        return Response(CalendariConfigSerializer(config).data)

    def patch(self, request):
        config, _ = CalendariConfig.objects.get_or_create(usuari=request.user)
        ser = CalendariConfigSerializer(config, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class MicrosoftOAuthInitView(APIView):
    """Redirect user to Microsoft OAuth2 consent page."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings as dj_settings
        from django.http import HttpResponseRedirect
        if not getattr(dj_settings, 'MS_CLIENT_ID', ''):
            return HttpResponseRedirect('/portal/calendari/?ms_config=0')
        from .microsoft import MicrosoftGraphClient
        import hashlib
        state = hashlib.sha256(f'{request.user.pk}-ms-oauth'.encode()).hexdigest()[:16]
        request.session['ms_oauth_state'] = state
        url = MicrosoftGraphClient.get_auth_url(state=state)
        return HttpResponseRedirect(url)


class MicrosoftOAuthCallbackView(APIView):
    """Handle OAuth2 callback and store tokens."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .microsoft import MicrosoftGraphClient
        from django.utils import timezone
        from datetime import timedelta

        code = request.query_params.get('code')
        state = request.query_params.get('state')
        session_state = request.session.get('ms_oauth_state', '')

        from django.http import HttpResponseRedirect
        from django.contrib import messages as dj_messages

        if not code or state != session_state:
            dj_messages.error(request._request if hasattr(request, '_request') else request, 'Error OAuth: estat invàlid.')
            return HttpResponseRedirect('/portal/calendari/')

        try:
            token_data = MicrosoftGraphClient.exchange_code(code)
        except Exception as e:
            logger.error('MS OAuth error: %s', e)
            return HttpResponseRedirect('/portal/calendari/?ms_error=1')

        config, _ = CalendariConfig.objects.get_or_create(usuari=request.user)
        config.ms_access_token = token_data['access_token']
        config.ms_refresh_token = token_data.get('refresh_token', '')
        expires_in = token_data.get('expires_in', 3600)
        config.ms_token_expiry = timezone.now() + timedelta(seconds=expires_in)
        config.save(update_fields=['ms_access_token', 'ms_refresh_token', 'ms_token_expiry'])

        return HttpResponseRedirect('/portal/calendari/?ms_ok=1')
