import time
import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConsultaRAG, DocumentEmbedding
from .retriever import recuperar_context, construir_prompt_rag, generar_context_bbdd
from .serializers import ConsultaRAGSerializer, ConsultaRAGInputSerializer, ValoracioSerializer

logger = logging.getLogger(__name__)


class ConsultaRAGView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        inp = ConsultaRAGInputSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        d = inp.validated_data

        consulta = ConsultaRAG.objects.create(
            usuari=request.user,
            pregunta=d['pregunta'],
            filtres=d['filtres'],
        )

        t0 = time.monotonic()
        try:
            chunks = recuperar_context(
                d['pregunta'],
                top_k=d['top_k'],
                filtres=d['filtres'] or None,
                similitud_minima=d['similitud_minima'],
            )

            context_bbdd = generar_context_bbdd()

            if not chunks and not context_bbdd:
                if not DocumentEmbedding.objects.exists():
                    msg = ('El sistema RAG no té cap document indexat. '
                           'Contacta amb l\'administrador per indexar els documents.')
                else:
                    msg = 'No s\'he trobat informació rellevant per a aquesta pregunta.'
                consulta.estat = ConsultaRAG.Estat.COMPLETADA
                consulta.resposta = msg
                consulta.context_recuperat = []
                consulta.temps_ms = int((time.monotonic() - t0) * 1000)
                consulta.save()
                return Response(ConsultaRAGSerializer(consulta).data)

            from django.utils.translation import get_language
            idioma = get_language() or 'es'
            prompt = construir_prompt_rag(d['pregunta'], chunks, context_bbdd=context_bbdd, idioma=idioma[:2])

            from modules.licitaciones.extraccion.ollama.client import OllamaClient
            model = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')
            client = OllamaClient(model=model)
            resposta = client.generate(prompt=prompt)

            fonts = list({c.get('font_id', '') for c in chunks if c.get('font_id')})

            consulta.context_recuperat = chunks
            consulta.resposta = resposta or ''
            consulta.fonts_citades = fonts
            consulta.model_usat = model
            consulta.temps_ms = int((time.monotonic() - t0) * 1000)
            consulta.estat = ConsultaRAG.Estat.COMPLETADA
            consulta.save()

        except Exception as exc:
            logger.error('Error en consulta RAG %s: %s', consulta.pk, exc)
            consulta.estat = ConsultaRAG.Estat.ERROR
            consulta.error_msg = str(exc)
            consulta.temps_ms = int((time.monotonic() - t0) * 1000)
            consulta.save()
            return Response(
                {'error': 'Error processant la consulta RAG.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(ConsultaRAGSerializer(consulta).data, status=status.HTTP_201_CREATED)


class ConsultaRAGViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConsultaRAGSerializer

    def get_queryset(self):
        return ConsultaRAG.objects.filter(usuari=self.request.user).order_by('-creada_en')

    @action(detail=True, methods=['patch'])
    def valorar(self, request, pk=None):
        consulta = self.get_object()
        ser = ValoracioSerializer(consulta, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ConsultaRAGSerializer(consulta).data)
