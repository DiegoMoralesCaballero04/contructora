from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class ScrapingTriggerView(APIView):
    """POST /api/v1/scraping/executar/ — trigger a scraping job (for n8n)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import json
        from apps.scraping.tasks import scrape_licitaciones
        filtres = request.data.get('filtres', {})
        if isinstance(filtres, str):
            try:
                filtres = json.loads(filtres)
            except (json.JSONDecodeError, TypeError):
                filtres = {}
        max_pagines = int(request.data.get('max_pagines', 10))

        task = scrape_licitaciones.delay(filtres=filtres, max_pagines=max_pagines)
        return Response({'task_id': task.id, 'estat': 'encuat'}, status=status.HTTP_202_ACCEPTED)


class HealthView(APIView):
    """GET /api/v1/health/ — service health check."""
    permission_classes = []

    def get(self, request):
        from storage.utils import check_s3_health, debug_s3
        from apps.extraccion.ollama.client import OllamaClient

        s3_ok = check_s3_health()
        checks = {
            'django': True,
            's3': s3_ok,
            's3_debug': debug_s3() if not s3_ok else None,
            'ollama': OllamaClient().is_available(),
        }

        try:
            from mongo.client import get_mongo_client
            get_mongo_client().admin.command('ping')
            checks['mongodb'] = True
        except Exception:
            checks['mongodb'] = False

        all_ok = all(checks.values())
        return Response(
            {'status': 'ok' if all_ok else 'degraded', 'checks': checks},
            status=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
