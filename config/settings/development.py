from .base import *

DEBUG = True

try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
except ImportError:
    pass

INTERNAL_IPS = ['127.0.0.1']

# Use console email in dev unless overridden in .env
_anymail = ANYMAIL if isinstance(ANYMAIL, dict) else {}
if not _anymail.get('SENDGRID_API_KEY') and not _anymail.get('MAILGUN_API_KEY'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS — allow all in dev
CORS_ALLOW_ALL_ORIGINS = True
