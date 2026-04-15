"""
Base settings shared across all environments.
"""
from pathlib import Path
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
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
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
    'apps.api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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
# Use URL names, not paths — resolve_url() calls reverse() which respects
# SCRIPT_NAME so subpath deployments (e.g. /ARJournal/) work correctly.
LOGIN_REDIRECT_URL = 'author_dashboard'
LOGOUT_REDIRECT_URL = 'home'

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
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
USE_S3 = env('USE_S3')
if USE_S3:
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
    AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
    AWS_S3_ENDPOINT_URL = env('AWS_S3_ENDPOINT_URL', default='')
    AWS_DEFAULT_ACL = 'private'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/'
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / env('MEDIA_ROOT', default='media')

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
}

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

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@trans-act-journal.org')
SERVER_EMAIL = env('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
# Public URL of the site — used to build absolute URLs in emails.
SITE_URL = env('SITE_URL', default='https://trans-act-journal.org')

# Feature flags
DOI_ENABLED = env('DOI_ENABLED')
TURNITIN_ENABLED = env('TURNITIN_ENABLED')
AI_FEATURES_ENABLED = env('AI_FEATURES_ENABLED')

# Crossref / DOI
CROSSREF_LOGIN = env('CROSSREF_LOGIN', default='')
CROSSREF_PASSWORD = env('CROSSREF_PASSWORD', default='')
CROSSREF_DEPOSITOR_NAME = env('CROSSREF_DEPOSITOR_NAME', default='Trans/Act Journal')
CROSSREF_DEPOSITOR_EMAIL = env('CROSSREF_DEPOSITOR_EMAIL', default='')

# Turnitin
TURNITIN_API_KEY = env('TURNITIN_API_KEY', default='')
TURNITIN_BASE_URL = env('TURNITIN_BASE_URL', default='https://api.turnitin.com')

# OpenAI (AI features — disabled until key set)
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')
