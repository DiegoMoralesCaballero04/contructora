import logging
import mimetypes
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Document, VersioDocument, CategoriaDocument, AccesDocument
from .serializers import (
    DocumentSerializer, VersioDocumentSerializer,
    CategoriaDocumentSerializer, AccesDocumentSerializer,
)
from .services import pujar_document, descarregar_document, verificar_integritat, verificar_permisos

logger = logging.getLogger(__name__)


class CategoriaDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CategoriaDocumentSerializer
    queryset = CategoriaDocument.objects.prefetch_related('fills').filter(pare__isnull=True)


class DocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['categoria', 'estat', 'tipus', 'licitacio', 'oferta']
    search_fields = ['nom', 'descripcio', 'etiquetes']
    ordering_fields = ['creada_en', 'nom', 'mida_bytes']

    def get_queryset(self):
        return Document.objects.select_related(
            'categoria', 'pujat_per', 'versio_actual'
        ).exclude(estat=Document.Estat.ELIMINAT).order_by('-creada_en')

    def perform_create(self, serializer):
        fitxer = self.request.FILES.get('fitxer')
        if not fitxer:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'fitxer': 'Camp obligatori.'})

        mime = mimetypes.guess_type(fitxer.name)[0] or 'application/octet-stream'
        tipus = _mime_to_tipus(mime)

        document = serializer.save(
            pujat_per=self.request.user,
            nom_fitxer_original=fitxer.name,
            mime_type=mime,
            tipus=tipus,
        )
        fitxer_bytes = fitxer.read()
        notes = self.request.data.get('notes_versio', '')
        pujar_document(document, fitxer_bytes, notes_versio=notes, user=self.request.user)

    def perform_update(self, serializer):
        fitxer = self.request.FILES.get('fitxer')
        document = serializer.save()
        if fitxer:
            fitxer_bytes = fitxer.read()
            notes = self.request.data.get('notes_versio', '')
            pujar_document(document, fitxer_bytes, notes_versio=notes, user=self.request.user)

    def perform_destroy(self, instance):
        if not verificar_permisos(instance, self.request.user, 'ADMIN'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('No tens permís per eliminar aquest document.')
        instance.estat = Document.Estat.ELIMINAT
        instance.save(update_fields=['estat', 'actualitzada_en'])

    @action(detail=True, methods=['get'], url_path='descarregar')
    def descarregar(self, request, pk=None):
        document = self.get_object()
        if not verificar_permisos(document, request.user, 'LECTURA'):
            return Response({'detail': 'Accés denegat.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            versio_pk = request.query_params.get('versio')
            versio = None
            if versio_pk:
                versio = VersioDocument.objects.get(pk=versio_pk, document=document)
            url = descarregar_document(document, user=request.user, request=request, versio=versio)
            return Response({'url': url, 'expires_in': 3600})
        except Exception as e:
            logger.error('Error generant URL per document %s: %s', pk, e)
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='verificar-integritat')
    def verificar_integritat_view(self, request, pk=None):
        document = self.get_object()
        result = verificar_integritat(document)
        return Response(result)

    @action(detail=True, methods=['get'], url_path='versions')
    def versions(self, request, pk=None):
        document = self.get_object()
        versions = VersioDocument.objects.filter(document=document).select_related('creada_per')
        return Response(VersioDocumentSerializer(versions, many=True).data)

    @action(detail=True, methods=['get'], url_path='accessos')
    def accessos(self, request, pk=None):
        document = self.get_object()
        accessos = AccesDocument.objects.filter(document=document).select_related('usuari', 'versio')[:100]
        return Response(AccesDocumentSerializer(accessos, many=True).data)


def _mime_to_tipus(mime: str) -> str:
    mapping = {
        'application/pdf': 'PDF',
        'application/msword': 'WORD',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'WORD',
        'application/vnd.ms-excel': 'EXCEL',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'EXCEL',
    }
    if mime.startswith('image/'):
        return 'IMATGE'
    if mime.startswith('video/'):
        return 'VIDEO'
    return mapping.get(mime, 'ALTRES')
