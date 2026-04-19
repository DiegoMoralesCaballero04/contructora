from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Empresa
from .serializers import EmpresaSerializer


class EmpresaView(APIView):
    """
    GET  /api/v1/empresa/  → retrieve singleton
    PUT  /api/v1/empresa/  → full update
    PATCH /api/v1/empresa/ → partial update
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        empresa = Empresa.get()
        serializer = EmpresaSerializer(empresa, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        return self._update(request, partial=False)

    def patch(self, request):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        empresa = Empresa.get()
        serializer = EmpresaSerializer(
            empresa, data=request.data, partial=partial, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
