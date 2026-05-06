import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.audit.utils import log_action
from .models import Oferta, Pressupost, LiniaPressupost, SolicitudSubcontractista
from .serializers import (
    OfertaListSerializer, OfertaDetailSerializer, PressupostSerializer,
    LiniaPressupostSerializer, SolicitudSubcontractistaSerializer,
    TransicioEstatSerializer, PlaSeguretatSerializer,
)
from .services import crear_versio_oferta

logger = logging.getLogger(__name__)


class OfertaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = (
        Oferta.objects
        .select_related('licitacio', 'licitacio__organismo', 'responsable')
        .prefetch_related('pressupostos__linies', 'solicituds_subcontractista__contacte')
        .order_by('-creada_en')
    )

    def get_serializer_class(self):
        if self.action == 'list':
            return OfertaListSerializer
        return OfertaDetailSerializer

    def perform_create(self, serializer):
        oferta = serializer.save(responsable=self.request.user)
        log_action('CREATE', 'Oferta', oferta.pk, str(oferta), user=self.request.user, request=self.request)

    def perform_update(self, serializer):
        crear_versio_oferta(serializer.instance, self.request.user)
        oferta = serializer.save()
        log_action('UPDATE', 'Oferta', oferta.pk, str(oferta), user=self.request.user, request=self.request)

    @action(detail=True, methods=['post'], url_path='transicio-estat')
    def transicio_estat(self, request, pk=None):
        oferta = self.get_object()
        ser = TransicioEstatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        nou_estat = ser.validated_data['estat']
        try:
            crear_versio_oferta(oferta, request.user)
            oferta.transicionar_estat(nou_estat, user=request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        log_action(
            'UPDATE', 'Oferta', oferta.pk, f'{oferta} → {nou_estat}',
            changes={'estat': nou_estat}, user=request.user, request=request,
        )
        return Response(OfertaDetailSerializer(oferta, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='calcular-preu-optim')
    def calcular_preu_optim(self, request, pk=None):
        from .tasks import calcular_preu_optim_task
        oferta = self.get_object()
        calcular_preu_optim_task.delay(oferta.pk)
        return Response({'status': 'calculant', 'oferta_id': oferta.pk})

    @action(detail=True, methods=['post'], url_path='generar-pla-seguretat')
    def generar_pla_seguretat(self, request, pk=None):
        from .tasks import generar_pla_seguretat_ia
        oferta = self.get_object()
        generar_pla_seguretat_ia.delay(oferta.pk)
        return Response({'status': 'generant', 'oferta_id': oferta.pk})

    @action(detail=True, methods=['post'], url_path='enviar-solicituds')
    def enviar_solicituds(self, request, pk=None):
        from .tasks import enviar_solicituds_subcontractistes
        oferta = self.get_object()
        enviar_solicituds_subcontractistes.delay(oferta.pk)
        return Response({'status': 'enviant', 'oferta_id': oferta.pk})

    @action(detail=True, methods=['get'], url_path='pla-seguretat')
    def pla_seguretat(self, request, pk=None):
        oferta = self.get_object()
        pss = getattr(oferta, 'pla_seguretat', None)
        if not pss:
            return Response({'detail': 'No generat encara.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PlaSeguretatSerializer(pss).data)

    @action(detail=True, methods=['patch'], url_path='validar-pla-seguretat')
    def validar_pla_seguretat(self, request, pk=None):
        from django.utils import timezone
        oferta = self.get_object()
        pss = getattr(oferta, 'pla_seguretat', None)
        if not pss:
            return Response({'detail': 'No existeix.'}, status=status.HTTP_404_NOT_FOUND)
        contingut_revisat = request.data.get('contingut_revisat', '')
        pss.contingut_revisat = contingut_revisat
        pss.validat = True
        pss.validat_per = request.user
        pss.validat_en = timezone.now()
        pss.save(update_fields=['contingut_revisat', 'validat', 'validat_per', 'validat_en', 'actualitzat_en'])
        return Response(PlaSeguretatSerializer(pss).data)


class PressupostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PressupostSerializer

    def get_queryset(self):
        return Pressupost.objects.filter(
            oferta__pk=self.kwargs['oferta_pk']
        ).prefetch_related('linies')

    def perform_create(self, serializer):
        oferta_pk = self.kwargs['oferta_pk']
        from .models import Oferta
        oferta = Oferta.objects.get(pk=oferta_pk)
        Pressupost.objects.filter(oferta=oferta, actiu=True).update(actiu=False)
        ultima = Pressupost.objects.filter(oferta=oferta).order_by('-versio').first()
        versio = (ultima.versio + 1) if ultima else 1
        serializer.save(oferta=oferta, versio=versio, actiu=True)


class LiniaPressupostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LiniaPressupostSerializer

    def get_queryset(self):
        return LiniaPressupost.objects.filter(
            pressupost__pk=self.kwargs['pressupost_pk'],
            pressupost__oferta__pk=self.kwargs['oferta_pk'],
        )

    def perform_create(self, serializer):
        from .models import Pressupost
        pressupost = Pressupost.objects.get(
            pk=self.kwargs['pressupost_pk'],
            oferta__pk=self.kwargs['oferta_pk'],
        )
        serializer.save(pressupost=pressupost)


class SolicitudSubcontractistaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SolicitudSubcontractistaSerializer

    def get_queryset(self):
        return SolicitudSubcontractista.objects.filter(
            oferta__pk=self.kwargs['oferta_pk']
        ).select_related('contacte')

    def perform_create(self, serializer):
        from .models import Oferta
        oferta = Oferta.objects.get(pk=self.kwargs['oferta_pk'])
        serializer.save(oferta=oferta)
