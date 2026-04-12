import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    kwargs = {
        'region_name': settings.AWS_S3_REGION_NAME,
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
    }
    if settings.AWS_SESSION_TOKEN:
        kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN
    if settings.AWS_S3_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
    return boto3.client('s3', **kwargs)


def generate_s3_key(expediente_id: str, filename: str) -> str:
    """Generate a deterministic S3 key for a PDF plec."""
    safe_id = expediente_id.replace('/', '_').replace(' ', '_')
    return f'plecs/{safe_id}/{filename}'


def generate_informe_s3_key(expediente_id: str, informe_pk: int) -> str:
    """Generate a deterministic S3 key for an InformeIntern PDF."""
    safe_id = expediente_id.replace('/', '_').replace(' ', '_')
    return f'informes/{safe_id}/informe_{informe_pk}.pdf'


def upload_pdf_to_s3(pdf_bytes: bytes, s3_key: str) -> str:
    """Upload PDF bytes to S3 and return the key."""
    client = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType='application/pdf',
        )
        logger.info('PDF uploaded to s3://%s/%s', bucket, s3_key)
        return s3_key
    except ClientError as e:
        logger.error('S3 upload failed for key %s: %s', s3_key, e)
        raise


def download_pdf_from_s3(s3_key: str) -> bytes:
    """Download a PDF from S3 and return bytes."""
    client = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    response = client.get_object(Bucket=bucket, Key=s3_key)
    return response['Body'].read()


def get_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str:
    """Generate a pre-signed URL for temporary access to a PDF."""
    client = get_s3_client()
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=expiry_seconds,
        )
        return url
    except ClientError as e:
        logger.error('Presigned URL generation failed: %s', e)
        raise


def check_s3_health() -> bool:
    """Ping S3 to verify connectivity."""
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
        return True
    except Exception as e:
        logger.warning('S3 health check failed [%s]: %s', type(e).__name__, e)
        return False


def debug_s3() -> dict:
    """Returns detailed S3 connection info for debugging."""
    import botocore.exceptions
    result = {
        'bucket': settings.AWS_STORAGE_BUCKET_NAME,
        'region': settings.AWS_S3_REGION_NAME,
        'key_id_prefix': (settings.AWS_ACCESS_KEY_ID or '')[:8] + '...',
        'has_session_token': bool(settings.AWS_SESSION_TOKEN),
        'error': None,
        'ok': False,
    }
    try:
        client = get_s3_client()
        client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
        result['ok'] = True
    except botocore.exceptions.ClientError as e:
        code = e.response['Error']['Code']
        result['error'] = f'ClientError {code}: {e.response["Error"].get("Message", "")}'
    except botocore.exceptions.NoCredentialsError:
        result['error'] = 'NoCredentialsError: credencials no configurades'
    except botocore.exceptions.InvalidClientTokenId:
        result['error'] = 'InvalidClientTokenId: AWS_ACCESS_KEY_ID incorrecte'
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {e}'
    return result
