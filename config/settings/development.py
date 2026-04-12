from .base import *

DEBUG = True

# No Redis in dev — all tasks run synchronously in-process
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# django-celery-results for DB-backed results if a worker is ever run
INSTALLED_APPS += ['django_celery_results']

try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
except ImportError:
    pass

INTERNAL_IPS = ['127.0.0.1']

# Use console email in dev unless a real provider is configured in .env
_anymail = ANYMAIL if isinstance(ANYMAIL, dict) else {}
_has_provider = (
    _anymail.get('MAILERSEND_API_TOKEN') or
    _anymail.get('SENDGRID_API_KEY') or
    _anymail.get('MAILGUN_API_KEY')
)
if not _has_provider:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS — allow all in dev
CORS_ALLOW_ALL_ORIGINS = True
