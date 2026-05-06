import logging
from django.http import HttpResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmpresaProspect, CampanyaMarketing, PlantillaEmail, EnviamentEmail
from .serializers import (
    EmpresaProspectSerializer, CampanyaMarketingSerializer,
    PlantillaEmailSerializer, EnviamentEmailSerializer,
)

logger = logging.getLogger(__name__)

TRACKING_PIXEL = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!'
    b'\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


class EmpresaProspectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmpresaProspectSerializer
    queryset = EmpresaProspect.objects.order_by('-scoring', '-creada_en')
    filterset_fields = ['sector', 'estat', 'provincia', 'baixa_voluntaria']
    search_fields = ['nom', 'email_principal', 'persona_contacte']
    ordering_fields = ['scoring', 'creada_en', 'nom']

    @action(detail=False, methods=['post'], url_path='importar-des-licitacions')
    def importar_des_licitacions(self, request):
        from .tasks import importar_prospects_licitacions
        importar_prospects_licitacions.delay()
        return Response({'status': 'important en background'})

    @action(detail=False, methods=['post'], url_path='recalcular-scoring')
    def recalcular_scoring(self, request):
        from .tasks import actualitzar_scoring_prospects
        actualitzar_scoring_prospects.delay()
        return Response({'status': 'calculant en background'})

    @action(detail=True, methods=['post'], url_path='registrar-consentiment')
    def registrar_consentiment(self, request, pk=None):
        prospect = self.get_object()
        prospect.consentiment_gdpr = True
        prospect.data_consentiment = timezone.now()
        prospect.save(update_fields=['consentiment_gdpr', 'data_consentiment'])
        return Response({'consentiment_gdpr': True})


class CampanyaMarketingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CampanyaMarketingSerializer
    queryset = CampanyaMarketing.objects.select_related('plantilla').order_by('-creada_en')

    def perform_create(self, serializer):
        serializer.save(creada_per=self.request.user)

    @action(detail=True, methods=['post'], url_path='executar')
    def executar(self, request, pk=None):
        from .tasks import executar_campanya
        campanya = self.get_object()
        if campanya.estat not in (
            CampanyaMarketing.Estat.ESBORRANY, CampanyaMarketing.Estat.PROGRAMADA
        ):
            return Response(
                {'detail': f'No es pot executar en estat {campanya.estat}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        executar_campanya.delay(campanya.pk)
        return Response({'status': 'executant', 'campanya_id': campanya.pk})

    @action(detail=True, methods=['get'], url_path='enviaments')
    def enviaments(self, request, pk=None):
        campanya = self.get_object()
        envs = EnviamentEmail.objects.filter(campanya=campanya).select_related('prospect')
        return Response(EnviamentEmailSerializer(envs, many=True).data)


class PlantillaEmailViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PlantillaEmailSerializer
    queryset = PlantillaEmail.objects.filter(activa=True).order_by('-creada_en')


class UnsubscribeView(APIView):
    """GDPR unsubscribe endpoint — no auth needed."""
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            import uuid
            prospect = EmpresaProspect.objects.get(token_baixa=uuid.UUID(str(token)))
        except (EmpresaProspect.DoesNotExist, ValueError):
            raise Http404

        prospect.baixa_voluntaria = True
        prospect.data_baixa = timezone.now()
        prospect.save(update_fields=['baixa_voluntaria', 'data_baixa'])
        logger.info('Baixa voluntaria: %s (%s)', prospect.nom, prospect.email_principal)
        return HttpResponse(
            '<h2>Heu estat donat de baixa correctament.</h2>'
            '<p>No rebreu més comunicacions de la nostra empresa.</p>',
            content_type='text/html',
        )


class TrackingOpenView(APIView):
    """1x1 pixel tracking — no auth needed."""
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            import uuid
            enviament = EnviamentEmail.objects.get(tracking_token=uuid.UUID(str(token)))
            if not enviament.obert:
                enviament.obert = True
                enviament.obert_en = timezone.now()
                enviament.save(update_fields=['obert', 'obert_en'])
                from .models import CampanyaMarketing
                from django.db.models import F
                CampanyaMarketing.objects.filter(pk=enviament.campanya_id).update(
                    total_obertures=F('total_obertures') + 1
                )
        except Exception:
            pass
        return HttpResponse(TRACKING_PIXEL, content_type='image/gif')
