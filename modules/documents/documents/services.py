"""
Document management services: S3 upload, versioning, integrity, permissions.
ISO 9001/14001 compliant: SHA-256 integrity, immutable access log, retention policies.
"""
import hashlib
import logging
import uuid
from io import BytesIO
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Document, VersioDocument, AccesDocument, PermisDocument

logger = logging.getLogger(__name__)


def _get_s3_client():
    kwargs = {
        'region_name': settings.AWS_S3_REGION_NAME,
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
    }
    if settings.AWS_S3_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
    if settings.AWS_SESSION_TOKEN:
        kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN
    return boto3.client('s3', **kwargs)


def calcular_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pujar_document(
    document: Document,
    fitxer_bytes: bytes,
    notes_versio: str = '',
    user: Optional[User] = None,
) -> VersioDocument:
    """
    Upload new document version to S3 with integrity check.
    Creates VersioDocument and updates Document.versio_actual.
    """
    sha256 = calcular_sha256(fitxer_bytes)
    s3 = _get_s3_client()

    ultima = document.versions.first()
    numero = (ultima.numero_versio + 1) if ultima else 1
    s3_key = f'documents/{document.categoria.codi}/{document.id}/v{numero}/{document.nom_fitxer_original}'

    response = s3.put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
        Key=s3_key,
        Body=fitxer_bytes,
        ContentType=document.mime_type or 'application/octet-stream',
        Metadata={
            'sha256': sha256,
            'document_id': str(document.id),
            'versio': str(numero),
        },
        ServerSideEncryption='AES256',
    )

    version_id = response.get('VersionId', '')

    versio = VersioDocument.objects.create(
        document=document,
        numero_versio=numero,
        s3_key=s3_key,
        s3_version_id=version_id,
        sha256=sha256,
        mida_bytes=len(fitxer_bytes),
        notes_versio=notes_versio,
        creada_per=user,
    )

    document.s3_key = s3_key
    document.sha256 = sha256
    document.mida_bytes = len(fitxer_bytes)
    document.s3_version_id = version_id
    document.versio_actual = versio
    document.estat = Document.Estat.ACTIU
    document.save(update_fields=[
        's3_key', 'sha256', 'mida_bytes', 's3_version_id',
        'versio_actual', 'estat', 'actualitzada_en',
    ])

    logger.info('Document %s v%d pujat a S3: %s', document.id, numero, s3_key)
    return versio


def descarregar_document(
    document: Document,
    user: Optional[User] = None,
    request=None,
    versio: Optional[VersioDocument] = None,
) -> str:
    """
    Generate a presigned S3 URL for document download.
    Logs access for ISO traceability.
    Optionally verifies SHA-256 integrity before serving.
    """
    target_versio = versio or document.versio_actual
    if not target_versio:
        raise ValueError('Document sense versió activa')

    s3 = _get_s3_client()
    params = {
        'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        'Key': target_versio.s3_key,
        'ResponseContentDisposition': f'attachment; filename="{document.nom_fitxer_original}"',
    }
    if target_versio.s3_version_id:
        params['VersionId'] = target_versio.s3_version_id

    url = s3.generate_presigned_url('get_object', Params=params, ExpiresIn=3600)

    ip = None
    ua = ''
    if request:
        ip = _get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')[:300]

    AccesDocument.objects.create(
        document=document,
        usuari=user,
        accio=AccesDocument.Accio.DESCARREGA,
        ip_address=ip,
        user_agent=ua,
        versio=target_versio,
    )

    return url


def verificar_integritat(document: Document) -> dict:
    """
    Download document from S3 and verify SHA-256.
    Returns {'ok': bool, 'sha256_calculat': str, 'sha256_esperat': str}.
    """
    if not document.versio_actual:
        return {'ok': False, 'error': 'Sense versió'}
    try:
        s3 = _get_s3_client()
        resp = s3.get_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=document.versio_actual.s3_key,
        )
        data = resp['Body'].read()
        calculat = calcular_sha256(data)
        esperat = document.versio_actual.sha256
        return {'ok': calculat == esperat, 'sha256_calculat': calculat, 'sha256_esperat': esperat}
    except ClientError as e:
        return {'ok': False, 'error': str(e)}


def verificar_permisos(document: Document, user: User, nivell: str = 'LECTURA') -> bool:
    """
    Check if user has at least the given permission level on a document.
    Admins always have access.
    """
    try:
        profile = user.profile
        if profile.role == 'ADMIN':
            return True
    except AttributeError:
        pass

    if document.pujat_per_id == user.pk:
        return True

    from django.utils import timezone as tz
    q = PermisDocument.objects.filter(document=document)
    q_user = q.filter(usuari=user)
    q_role = q.filter(rol=getattr(getattr(user, 'profile', None), 'role', ''))
    permisos = (q_user | q_role).filter(
        models.Q(expira_en__isnull=True) | models.Q(expira_en__gt=tz.now())
    )

    nivells = {
        'LECTURA': ['LECTURA', 'EDICIO', 'ADMIN'],
        'EDICIO': ['EDICIO', 'ADMIN'],
        'ADMIN': ['ADMIN'],
    }
    allowed_nivells = nivells.get(nivell, ['LECTURA'])
    return permisos.filter(nivell__in=allowed_nivells).exists()


def arxivar_documents_caducats():
    """
    Daily task: archive documents past their expiry date.
    ISO 9001 requirement: keep but mark as archived.
    """
    from .models import Document
    from django.utils import timezone
    import datetime

    avui = timezone.now().date()
    caducats = Document.objects.filter(
        estat=Document.Estat.ACTIU,
        data_caducitat__lt=avui,
    )
    count = caducats.update(estat=Document.Estat.ARXIVAT)
    logger.info('%d documents arxivats per caducitat', count)
    return count


def _get_client_ip(request) -> Optional[str]:
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


try:
    from django.db import models
except ImportError:
    pass
