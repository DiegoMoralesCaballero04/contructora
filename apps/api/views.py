from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class ScrapingTriggerView(APIView):
    """POST /api/v1/scraping/executar/ — trigger a scraping job (for n8n).
    Always uses the single ScrapingTemplate. template_id param ignored for backward compatibility."""
    permission_classes = []

    def post(self, request):
        import json
        try:
            from modules.licitaciones.scraping.tasks import scrape_licitaciones
        except ImportError:
            return Response(
                {'error': 'scraping module not available'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        filtres = request.data.get('filtres') or {}
        if isinstance(filtres, str):
            try:
                filtres = json.loads(filtres)
            except (json.JSONDecodeError, TypeError):
                filtres = {}

        raw_max = request.data.get('max_pagines')
        max_pagines = int(raw_max) if raw_max is not None else None

        task = scrape_licitaciones.delay(
            filtres=filtres or None,
            max_pagines=max_pagines,
        )
        return Response({'task_id': task.id, 'estat': 'encuat'}, status=status.HTTP_202_ACCEPTED)


class HealthView(APIView):
    """GET /api/v1/health/ — service health check."""
    permission_classes = []

    def get(self, request):
        checks = {'django': True}

        try:
            from core.storage.utils import check_s3_health, debug_s3
            s3_ok = check_s3_health()
            checks['s3'] = s3_ok
            if not s3_ok:
                checks['s3_debug'] = debug_s3()
        except ImportError:
            pass

        try:
            from modules.licitaciones.extraccion.ollama.client import OllamaClient
            checks['ollama'] = OllamaClient().is_available()
        except ImportError:
            pass

        try:
            from core.mongo.client import get_mongo_client
            get_mongo_client().admin.command('ping')
            checks['mongodb'] = True
        except ImportError:
            pass
        except Exception:
            checks['mongodb'] = False

        all_ok = all(checks.values())
        return Response(
            {'status': 'ok' if all_ok else 'degraded', 'checks': checks},
            status=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
