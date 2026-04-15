"""
Staging settings — app served at a subpath on a shared server
(e.g. https://misc.lmta.lt/ARJournal).

Set SCRIPT_NAME=/ARJournal in .env. The WSGI-level SCRIPT_NAME injection is
handled by config/wsgi.py, which reads SCRIPT_NAME from os.environ and sets
it on every incoming request. Django uses it for URL generation automatically.

We deliberately do NOT set FORCE_SCRIPT_NAME here. allauth's AccountMiddleware
checks that request.path starts with FORCE_SCRIPT_NAME, but Nginx strips the
subpath prefix before forwarding (proxy_pass with trailing slash), so
request.path_info arrives as '/' — making that check always fail.
"""
from .production import *  # noqa: F401, F403

# ── Subpath URL prefixes ──────────────────────────────────────────────────────
# Must match the SCRIPT_NAME value in .env so that Nginx can route
# /ARJournal/static/ and /ARJournal/media/ directly from disk.
SCRIPT_NAME = env('SCRIPT_NAME', default='/ARJournal')
STATIC_URL = f'{SCRIPT_NAME}/static/'
MEDIA_URL = f'{SCRIPT_NAME}/media/'

# ── Proxy / SSL ───────────────────────────────────────────────────────────────
# SSL is terminated at Nginx — the app receives plain HTTP from Gunicorn.
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Shorter HSTS for staging.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
