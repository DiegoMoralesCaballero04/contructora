from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Licitacion
from .serializers import LicitacionListSerializer, LicitacionDetailSerializer
from .filters import LicitacionFilter


class LicitacionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Licitacion.objects.select_related('organismo').prefetch_related('criterios')
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = LicitacionFilter
    search_fields = ['titulo', 'expediente_id', 'organismo__nombre']
    ordering_fields = ['importe_base', 'fecha_publicacion', 'fecha_limite_oferta', 'creado_en']
    ordering = ['-creado_en']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LicitacionDetailSerializer
        return LicitacionListSerializer

    @action(detail=True, methods=['post'], url_path='marcar-revisada')
    def marcar_revisada(self, request, pk=None):
        licitacion = self.get_object()
        licitacion.estado = Licitacion.Estado.REVISADA
        licitacion.save(update_fields=['estado', 'actualizado_en'])
        return Response({'estado': licitacion.estado})

    @action(detail=True, methods=['post'], url_path='marcar-descartada')
    def marcar_descartada(self, request, pk=None):
        licitacion = self.get_object()
        licitacion.estado = Licitacion.Estado.DESCARTADA
        licitacion.save(update_fields=['estado', 'actualizado_en'])
        return Response({'estado': licitacion.estado})

    @action(detail=False, methods=['get'], url_path='resum-diari')
    def resum_diari(self, request):
        from django.utils import timezone
        avui = timezone.now().date()
        noves = Licitacion.objects.filter(
            creado_en__date=avui, estado=Licitacion.Estado.NOVA
        ).count()
        return Response({
            'data': avui.isoformat(),
            'noves_avui': noves,
            'total_actives': Licitacion.objects.exclude(
                estado__in=[Licitacion.Estado.DESCARTADA, Licitacion.Estado.DESIERTA]
            ).count(),
        })
