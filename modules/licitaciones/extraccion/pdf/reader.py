"""
Download a PDF from S3 and extract its text content using pdfplumber.
"""
import io
import logging
import pdfplumber
from core.storage.utils import download_pdf_from_s3

logger = logging.getLogger(__name__)

MAX_PAGES = 50  # Only process first N pages to limit LLM context size


def extract_text_from_s3_pdf(s3_key: str, max_pages: int = MAX_PAGES) -> str:
    """
    Download a PDF from S3 and extract all text up to max_pages.
    Returns a single string with all extracted text.
    """
    logger.debug('Extracting text from S3 PDF: %s', s3_key)
    pdf_bytes = download_pdf_from_s3(s3_key)
    return extract_text_from_bytes(pdf_bytes, max_pages=max_pages)


def extract_text_from_bytes(pdf_bytes: bytes, max_pages: int = MAX_PAGES) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    text_parts = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(total_pages, max_pages)
            logger.debug('PDF has %d pages, processing %d', total_pages, pages_to_process)

            for i, page in enumerate(pdf.pages[:pages_to_process]):
                try:
                    page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                    if page_text:
                        text_parts.append(f'--- Pàgina {i + 1} ---\n{page_text}')
                except Exception as e:
                    logger.warning('Failed to extract page %d: %s', i + 1, e)

    except Exception as e:
        logger.error('pdfplumber failed: %s', e)
        # Fallback to pypdf
        text_parts = _extract_with_pypdf(pdf_bytes, max_pages)

    full_text = '\n'.join(text_parts)
    logger.debug('Extracted %d characters from PDF', len(full_text))
    return full_text


def _extract_with_pypdf(pdf_bytes: bytes, max_pages: int) -> list[str]:
    """Fallback text extraction using pypdf."""
    from pypdf import PdfReader
    text_parts = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for i, page in enumerate(reader.pages[:max_pages]):
            text = page.extract_text()
            if text:
                text_parts.append(f'--- Pàgina {i + 1} ---\n{text}')
    except Exception as e:
        logger.error('pypdf fallback also failed: %s', e)
    return text_parts
