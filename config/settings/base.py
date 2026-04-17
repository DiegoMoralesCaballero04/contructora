import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('DJANGO_SECRET_KEY', default='insecure-dev-key-change-me')
DEBUG = env.bool('DJANGO_DEBUG', default=False)
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Third-party
    'rest_framework',
    'django_filters',
    'corsheaders',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    # Core (always present)
    'core.audit',
    # UI layers (always present)
    'apps.portal',
    'apps.api',
]

# Optional modules — included only when the directory is present.
# To disable a module, remove its directory from modules/.
_OPTIONAL_MODULES = [
    'modules.licitaciones.licitaciones',
    'modules.licitaciones.scraping',
    'modules.licitaciones.extraccion',
    'modules.licitaciones.alertas',
    'modules.rrhh.rrhh',
]

for _mod in _OPTIONAL_MODULES:
    _mod_path = BASE_DIR / _mod.replace('.', '/')
    if _mod_path.is_dir():
        INSTALLED_APPS.append(_mod)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── PostgreSQL ────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('POSTGRES_DB', default='construtech'),
        'USER': env('POSTGRES_USER', default='construtech'),
        'PASSWORD': env('POSTGRES_PASSWORD', default='construtech_password'),
        'HOST': env('POSTGRES_HOST', default='localhost'),
        'PORT': env('POSTGRES_PORT', default='5432'),
    }
}

# ── MongoDB (used directly via pymongo) ──────────────────────────
MONGO_HOST = env('MONGO_HOST', default='localhost')
MONGO_PORT = env.int('MONGO_PORT', default=27017)
MONGO_DB = env('MONGO_DB', default='construtech_raw')
MONGO_USER = env('MONGO_USER', default='')
MONGO_PASSWORD = env('MONGO_PASSWORD', default='')

# ── Redis / Celery ────────────────────────────────────────────────
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Madrid'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ── AWS S3 ────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_SESSION_TOKEN = env('AWS_SESSION_TOKEN', default='')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='construtech-licitaciones')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='eu-south-2')
AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default='')
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

# ── Ollama ────────────────────────────────────────────────────────
OLLAMA_BASE_URL = env('OLLAMA_BASE_URL', default='http://localhost:11434')
OLLAMA_MODEL = env('OLLAMA_MODEL', default='llama3.2:3b')

# ── Telegram ──────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_CHAT_ID = env('TELEGRAM_CHAT_ID', default='')

# ── Email ─────────────────────────────────────────────────────────
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@construtech-ia.local')

# ── API ───────────────────────────────────────────────────────────
API_KEY = env('API_KEY', default='construtech-api-key')

# ── DRF ───────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'apps.api.authentication.ApiKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
        'rest_framework.filters.SearchFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.api.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'CONSTRUTECH-IA API',
    'DESCRIPTION': 'API per a la gestió automatitzada de licitacions públiques.',
    'VERSION': '1.0.0',
}

# ── Static / Media ────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
LANGUAGES = [
    ('es', 'Español'),
    ('ca', 'Valencià'),
    ('en', 'English'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']
TIME_ZONE = 'Europe/Madrid'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/portal/login/'
LOGIN_REDIRECT_URL = '/portal/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'modules': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'core': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}
