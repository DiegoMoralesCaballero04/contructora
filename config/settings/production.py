from .base import *  # noqa

DEBUG = False

SECURE_SSL_REDIRECT = False  # Set True when HTTPS is configured
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Use S3 for media files in production
DEFAULT_FILE_STORAGE = 'storage.backends.S3MediaStorage'
