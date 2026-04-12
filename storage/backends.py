from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings


class S3MediaStorage(S3Boto3Storage):
    """Storage backend for user-uploaded and scraped media files (PDFs)."""
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = 'media'
    file_overwrite = False


class S3PDFStorage(S3Boto3Storage):
    """Storage backend specifically for licitacion PDF plecs."""
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    location = 'plecs'
    file_overwrite = False
    default_acl = 'private'
