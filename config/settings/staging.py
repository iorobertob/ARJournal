"""
Staging settings — app served at https://misc.lmta.lt/journal (subpath).

Extends production settings and overrides what changes for subpath deployment.
Nginx strips the /journal prefix before forwarding to Gunicorn (proxy_pass with
trailing slash). FORCE_SCRIPT_NAME tells Django to prefix all generated URLs
so links, redirects, and form actions all resolve correctly in the browser.
"""
from .production import *  # noqa: F401, F403

# ── Subpath configuration ─────────────────────────────────────────────────────
SCRIPT_NAME = '/journal'
FORCE_SCRIPT_NAME = SCRIPT_NAME

# Static and media URLs must include the subpath prefix so that Nginx can
# distinguish them from the app routes and serve them directly from disk.
STATIC_URL = f'{SCRIPT_NAME}/static/'
MEDIA_URL = f'{SCRIPT_NAME}/media/'

# ── Proxy / SSL ───────────────────────────────────────────────────────────────
# SSL is terminated at Nginx on misc.lmta.lt — don't redirect again inside app.
SECURE_SSL_REDIRECT = False
# Tell Django the request was HTTPS (Nginx sets X-Forwarded-Proto).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Shorter HSTS for staging — easy to roll back if something goes wrong.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
