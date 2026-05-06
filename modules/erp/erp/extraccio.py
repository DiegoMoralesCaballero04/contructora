"""
IA extraction service for ERP documents (invoices, delivery notes, orders).
Reads a PDF or image file and uses Ollama to extract structured data.
"""
import io
import json
import logging

logger = logging.getLogger(__name__)


def _llegir_text_pdf(fitxer) -> str:
    """Extract plain text from a PDF file-like object using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(fitxer)
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return '\n'.join(parts)[:8000]
    except Exception as e:
        logger.warning('pypdf extraction failed: %s', e)
        return ''


def _llegir_text_imatge(fitxer) -> str:
    """OCR an image file using pytesseract if available."""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(fitxer)
        return pytesseract.image_to_string(img, lang='spa+cat+eng')[:8000]
    except Exception as e:
        logger.warning('OCR extraction failed: %s', e)
        return ''


def extraure_text_document(fitxer_field) -> str:
    """Given a FieldFile (from model.document_adjunt), extract its text."""
    if not fitxer_field:
        return ''
    nom = fitxer_field.name.lower()
    try:
        fitxer_field.open('rb')
        contingut = fitxer_field.read()
        fitxer_field.close()
    except Exception:
        return ''

    buf = io.BytesIO(contingut)
    if nom.endswith('.pdf'):
        return _llegir_text_pdf(buf)
    elif any(nom.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp')):
        return _llegir_text_imatge(buf)
    return ''


_PROMPT_FACTURA = """Ets un sistema d'extracció d'informació de factures.
Analitza el text de la factura i extreu les dades en format JSON estricte.
Retorna ÚNICAMENT el JSON, sense cap text addicional.

Format de sortida:
{{
  "numero_factura": "",
  "data_emisio": "YYYY-MM-DD o buit",
  "data_venciment": "YYYY-MM-DD o buit",
  "proveidor_nom": "",
  "proveidor_nif": "",
  "client_nom": "",
  "client_nif": "",
  "base_imponible": 0.00,
  "tipus_iva": 21,
  "import_iva": 0.00,
  "total": 0.00,
  "irpf_percentatge": 0,
  "retencio_irpf": 0.00,
  "concepte": "",
  "forma_pago": ""
}}

TEXT DE LA FACTURA:
{text}

JSON:"""

_PROMPT_ALBARA = """Ets un sistema d'extracció d'albarans de lliurament.
Analitza el text i extreu les dades en format JSON estricte.
Retorna ÚNICAMENT el JSON.

Format:
{{
  "numero_albara": "",
  "data": "YYYY-MM-DD o buit",
  "proveidor_nom": "",
  "client_nom": "",
  "linies": [
    {{"descripcio": "", "quantitat": 0, "unitat": ""}}
  ],
  "referencia_comanda": ""
}}

TEXT:
{text}

JSON:"""

_PROMPT_PEDIDO = """Ets un sistema d'extracció de comandes/pedidos.
Analitza el text i extreu les dades en format JSON estricte.
Retorna ÚNICAMENT el JSON.

Format:
{{
  "numero_pedido": "",
  "data": "YYYY-MM-DD o buit",
  "client_nom": "",
  "client_nif": "",
  "linies": [
    {{"descripcio": "", "quantitat": 0, "preu_unitari": 0.00}}
  ],
  "referencia_client": "",
  "data_entrega": "YYYY-MM-DD o buit"
}}

TEXT:
{text}

JSON:"""


def extraure_dades_ia(text: str, tipus: str = 'factura') -> dict:
    """
    Call Ollama to extract structured data from document text.
    tipus: 'factura' | 'albara' | 'pedido'
    Returns a dict with extracted fields, or empty dict on failure.
    """
    if not text.strip():
        return {}

    prompts = {
        'factura': _PROMPT_FACTURA,
        'albara': _PROMPT_ALBARA,
        'pedido': _PROMPT_PEDIDO,
    }
    prompt_template = prompts.get(tipus, _PROMPT_FACTURA)
    prompt = prompt_template.format(text=text[:6000])

    try:
        from django.conf import settings
        from modules.licitaciones.extraccion.ollama.client import OllamaClient
        model = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')
        client = OllamaClient(model=model)
        resposta = client.generate(prompt=prompt, timeout=60)

        resposta = resposta.strip()
        if resposta.startswith('```'):
            lines = resposta.split('\n')
            resposta = '\n'.join(lines[1:-1] if lines[-1].startswith('```') else lines[1:])

        return json.loads(resposta)
    except json.JSONDecodeError as e:
        logger.warning('IA extraction JSON parse error: %s', e)
        return {}
    except Exception as e:
        logger.error('IA extraction error: %s', e)
        return {}
