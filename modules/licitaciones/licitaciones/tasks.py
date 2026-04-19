import logging

from celery import shared_task

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generar_pdf_informe(self, informe_pk: int):
    """
    Generates a PDF for an InformeIntern using Playwright (headless Chromium),
    uploads it to S3, and saves the key + presigned URL on the informe.
    """
    from .models import InformeIntern
    from core.storage.utils import generate_informe_s3_key, upload_pdf_to_s3, get_presigned_url

    try:
        informe = InformeIntern.objects.select_related(
            'licitacion__organismo', 'autor'
        ).get(pk=informe_pk)
    except InformeIntern.DoesNotExist:
        logger.error('InformeIntern %d not found', informe_pk)
        return

    logger.info('Generating PDF for informe %d (licitació %s)', informe_pk, informe.licitacion.estado)

    try:
        pdf_bytes = _render_informe_to_pdf(informe)
    except Exception as exc:
        logger.error('PDF render failed for informe %d: %s', informe_pk, exc)
        raise self.retry(exc=exc)

    try:
        s3_key = generate_informe_s3_key(informe.licitacion.expediente_id, informe_pk)
        upload_pdf_to_s3(pdf_bytes, s3_key)
        presigned_url = get_presigned_url(s3_key, expiry_seconds=365 * 24 * 3600)

        informe.pdf_s3_key = s3_key
        informe.pdf_s3_url = presigned_url
        informe.save(update_fields=['pdf_s3_key', 'pdf_s3_url', 'actualizado_en'])

        logger.info('PDF uploaded to S3: %s', s3_key)
    except Exception as exc:
        logger.error('S3 upload failed for informe %d: %s', informe_pk, exc)
        raise self.retry(exc=exc)


def _render_informe_to_pdf(informe) -> bytes:
    """
    Renders the informe_print.html Django template and converts it to PDF
    using Playwright's Chromium (already available in the base Docker image).
    """
    from django.template.loader import render_to_string
    from playwright.sync_api import sync_playwright

    html = render_to_string('portal/informe_print.html', {'informe': informe})

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        pdf_bytes = page.pdf(
            format='A4',
            print_background=True,
            margin={'top': '20mm', 'bottom': '20mm', 'left': '18mm', 'right': '18mm'},
        )
        browser.close()

    return pdf_bytes
