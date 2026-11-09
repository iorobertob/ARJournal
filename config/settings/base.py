"""
Base settings shared across all environments.
"""
from pathlib import Path
from urllib.parse import urlparse as _urlparse
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    ORCID_OAUTH_ENABLED=(bool, False),
    DOI_ENABLED=(bool, False),
    TURNITIN_ENABLED=(bool, False),
    AI_FEATURES_ENABLED=(bool, False),
    USE_S3=(bool, False),
)

environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# ── Site URL — single source of truth for all URL-derived settings ────────────
# Set this in .env:
#   dev:        SITE_URL=http://localhost:5002
#   staging:    SITE_URL=https://misc.lmta.lt/journal   (subpath)
#   production: SITE_URL=https://inact.lmta.lt          (root domain)
#
# The path component (e.g. /ARJournal) prefixes STATIC_URL, MEDIA_URL, and the
# auth redirect URLs. For root-path domains the path is empty and all URLs are
# normal slash-only values. SCRIPT_NAME is injected by wsgi.py from this same value.
SITE_URL = env('SITE_URL', default='http://localhost:5002')
_site    = _urlparse(SITE_URL)
_prefix  = _site.path.rstrip('/')   # '/ARJournal' or '' for root domains

# CSRF — default to the scheme+host from SITE_URL; override in .env if needed
# (comma-separated values, not Python list syntax).
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=[f'{_site.scheme}://{_site.netloc}'] if _site.netloc else [],
)

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.orcid',
    'django_htmx',
    'storages',
    'django_celery_results',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.journal',
    'apps.submissions',
    'apps.documents',
    'apps.editorial',
    'apps.reviewers',
    'apps.reviews',
    'apps.notifications',
    'apps.production',
    'apps.governance',
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'config.middleware.HTMLNoCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
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
                'apps.journal.context_processors.journal_config',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME', default='transact_journal'),
        'USER': env('DB_USER', default='transact'),
        'PASSWORD': env('DB_PASSWORD', default='devpassword'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}

# Auth
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# django-allauth
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_SUBJECT_PREFIX = ''   # our subject templates already include the journal name
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3

# Anti-abuse: hardened signup form (honeypot + disposable-email block + Turnstile).
ACCOUNT_FORMS = {'signup': 'apps.accounts.forms.SignupForm'}

# Rate limits (allauth built-in). Format: "<count>/<period>/<scope>", comma-separated.
ACCOUNT_RATE_LIMITS = {
    'signup': '6/m/ip,20/h/ip',          # cap automated registration bursts
    'login_failed': '5/5m/ip',           # brute-force protection
    'confirm_email': '1/3m/key',         # limit verification-email resends
    'reset_password': '5/m/ip,20/h/ip',  # limit password-reset email abuse
}

# Cloudflare Turnstile (bot challenge on signup). Empty secret → disabled (dev/test).
TURNSTILE_SITE_KEY = env('TURNSTILE_SITE_KEY', default='')
TURNSTILE_SECRET_KEY = env('TURNSTILE_SECRET_KEY', default='')
LOGIN_URL            = f'{_prefix}/accounts/login/'
LOGIN_REDIRECT_URL   = f'{_prefix}/author/dashboard/'
LOGOUT_REDIRECT_URL  = f'{_prefix}/' if _prefix else '/'

# ORCID OAuth
SOCIALACCOUNT_PROVIDERS = {}
ORCID_OAUTH_ENABLED = env('ORCID_OAUTH_ENABLED')
if ORCID_OAUTH_ENABLED:
    SOCIALACCOUNT_PROVIDERS['orcid'] = {
        'BASE_DOMAIN': 'orcid.org',
        'MEMBER_API': False,
        'APP': {
            'client_id': env('ORCID_CLIENT_ID', default=''),
            'secret': env('ORCID_CLIENT_SECRET', default=''),
        }
    }

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = f'{_prefix}/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
# Static/media storage backends are configured together in the STORAGES dict
# below (after USE_S3 is known). Django 5.x ignores the old STATICFILES_STORAGE /
# DEFAULT_FILE_STORAGE settings, so those must NOT be used here.

# Media files
USE_S3 = env('USE_S3')
if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default='')
    AWS_DEFAULT_ACL = 'private'
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/'
else:
    MEDIA_URL = f'{_prefix}/media/'
    MEDIA_ROOT = BASE_DIR / env('MEDIA_ROOT', default='media')

# Storage backends (Django 5.x STORAGES API — replaces the removed
# STATICFILES_STORAGE / DEFAULT_FILE_STORAGE settings).
#  • staticfiles → WhiteNoise: compresses assets and writes content-hashed
#    filenames + a manifest, so collectstatic busts caches on every deploy.
#  • default (media) → S3 when USE_S3 is on, otherwise local filesystem.
# development.py overrides this dict (plain + cache-busting static storage).
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage' if USE_S3
        else 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ── Media streaming / protected delivery ─────────────────────────────────────
# Video & audio are transcoded to HLS and served only through signed, short-lived
# URLs (never as a directly downloadable file). See apps/production/media_access.py,
# apps/production/transcode.py and the streaming view in apps/production/views.py.
MEDIA_STREAMING_ENABLED = env.bool('MEDIA_STREAMING_ENABLED', default=True)
MEDIA_SIGNED_URL_TTL = env.int('MEDIA_SIGNED_URL_TTL', default=10800)   # seconds (3h)
# In production Nginx serves the bytes via X-Accel-Redirect (fast, no app I/O);
# in dev (runserver, no Nginx) the view streams the file itself.
USE_X_ACCEL = env.bool('USE_X_ACCEL', default=not DEBUG)
# ffmpeg/ffprobe binaries and the HLS bitrate ladder (heights, px). Renditions are
# capped at the source height so nothing is upscaled.
FFMPEG_BIN = env('FFMPEG_BIN', default='ffmpeg')
FFPROBE_BIN = env('FFPROBE_BIN', default='ffprobe')
HLS_LADDER = [1080, 720, 360]
# Media file extensions that must never be served directly (streamed only).
PROTECTED_MEDIA_EXTS = (
    '.m3u8', '.ts', '.m4s', '.mp4', '.mov', '.webm', '.mkv',
    '.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg',
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# Route CPU-heavy transcoding to a dedicated low-concurrency worker (inact-transcode
# systemd unit) so it never starves the web/email worker.
CELERY_TASK_ROUTES = {
    'apps.production.tasks.transcode_asset': {'queue': 'transcode'},
    'apps.production.tasks.generate_submission_cover_derivatives': {'queue': 'transcode'},
}

# Cache. Set REDIS_CACHE_URL in production so allauth's signup/login rate limits
# are shared across all Gunicorn workers (counters live in the cache). Left unset
# (e.g. dev, which has no Redis) falls back to Django's per-process memory cache.
_redis_cache_url = env('REDIS_CACHE_URL', default='')
if _redis_cache_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': _redis_cache_url,
        }
    }

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'cleanup-pdf-exports': {
        'task': 'apps.production.tasks.cleanup_expired_pdf_exports',
        'schedule': crontab(hour='*/6'),
    },
    'send-review-reminders': {
        'task': 'apps.notifications.tasks.send_review_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    'purge-unverified-accounts': {
        'task': 'apps.notifications.tasks.purge_unverified_accounts',
        'schedule': crontab(hour=3, minute=30),
    },
}

# Account purge allowlist — accounts the unverified-account cleanup must NEVER
# delete. Domains here are a permanent, code-level skip (lmta.lt by default);
# additional emails/domains can be managed at runtime via the DB allowlist
# (`python manage.py purge_allowlist add …`). Both are honored by the task and
# by the daily beat run, so exempt accounts never even appear in a dry run.
ACCOUNT_PURGE_PROTECTED_DOMAINS = env.list(
    'ACCOUNT_PURGE_PROTECTED_DOMAINS', default=['lmta.lt'])
ACCOUNT_PURGE_PROTECTED_EMAILS = env.list(
    'ACCOUNT_PURGE_PROTECTED_EMAILS', default=[])

# Email (django-anymail)
ANYMAIL_BACKEND = env('ANYMAIL_BACKEND', default='console')
if ANYMAIL_BACKEND == 'mailersend':
    EMAIL_BACKEND = 'anymail.backends.mailersend.EmailBackend'
    ANYMAIL = {'MAILERSEND_API_TOKEN': env('MAILERSEND_API_TOKEN', default='')}
elif ANYMAIL_BACKEND == 'sendgrid':
    EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
    ANYMAIL = {'SENDGRID_API_KEY': env('SENDGRID_API_KEY', default='')}
elif ANYMAIL_BACKEND == 'mailgun':
    EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'
    ANYMAIL = {
        'MAILGUN_API_KEY': env('MAILGUN_API_KEY', default=''),
        'MAILGUN_SENDER_DOMAIN': env('MAILGUN_SENDER_DOMAIN', default=''),
    }
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    ANYMAIL = {}

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@in-act-journal.org')
SERVER_EMAIL = env('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Feature flags
DOI_ENABLED = env('DOI_ENABLED')
TURNITIN_ENABLED = env('TURNITIN_ENABLED')
AI_FEATURES_ENABLED = env('AI_FEATURES_ENABLED')

# Crossref / DOI
CROSSREF_LOGIN = env('CROSSREF_LOGIN', default='')
CROSSREF_PASSWORD = env('CROSSREF_PASSWORD', default='')
CROSSREF_DEPOSITOR_NAME = env('CROSSREF_DEPOSITOR_NAME', default='inACT Journal')
CROSSREF_DEPOSITOR_EMAIL = env('CROSSREF_DEPOSITOR_EMAIL', default='')

# Turnitin
TURNITIN_API_KEY = env('TURNITIN_API_KEY', default='')
TURNITIN_BASE_URL = env('TURNITIN_BASE_URL', default='https://api.turnitin.com')

# OpenAI (AI features — disabled until key set)
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
