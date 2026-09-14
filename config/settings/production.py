from .base import *

DEBUG = False

# Security
# Nginx terminates TLS and proxies to Gunicorn over http, forwarding the original
# scheme in X-Forwarded-Proto. Trust it so request.is_secure() is True — without
# this, SECURE_SSL_REDIRECT loops forever and every generated absolute URL
# (canonical tags, sitemap, emails) comes out as insecure http://.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CORS — restrict to configured origins in production
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_ALL_ORIGINS = False

# Sentry (optional)
import os
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)
