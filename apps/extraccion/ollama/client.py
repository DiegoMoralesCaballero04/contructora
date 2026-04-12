"""
HTTP client wrapper for the Ollama REST API.
Docs: https://github.com/ollama/ollama/blob/main/docs/api.md
"""
import json
import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip('/')
        self.model = model or settings.OLLAMA_MODEL

    def generate(self, prompt: str, timeout: int = 120) -> str:
        """
        Send a prompt to Ollama and return the response text.
        Uses the /api/generate endpoint (non-streaming).
        """
        url = f'{self.base_url}/api/generate'
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': 0.1,   # Low temp for structured extraction
                'num_predict': 2048,
            },
        }
        logger.debug('Ollama request to %s (model=%s, prompt_len=%d)', url, self.model, len(prompt))

        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get('response', '')
                logger.debug('Ollama response received (%d chars)', len(response_text))
                return response_text
        except httpx.TimeoutException:
            logger.error('Ollama request timed out after %ds', timeout)
            raise
        except httpx.HTTPStatusError as e:
            logger.error('Ollama HTTP error: %s', e)
            raise

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is loaded."""
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f'{self.base_url}/api/tags')
                if resp.status_code != 200:
                    return False
                models = [m['name'] for m in resp.json().get('models', [])]
                return any(self.model in m for m in models)
        except Exception:
            return False

    def pull_model(self) -> bool:
        """Pull the configured model if not already available."""
        logger.info('Pulling Ollama model: %s', self.model)
        try:
            with httpx.Client(timeout=600) as client:
                resp = client.post(
                    f'{self.base_url}/api/pull',
                    json={'name': self.model, 'stream': False},
                )
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error('Model pull failed: %s', e)
            return False
