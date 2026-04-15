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
# Use a private variable so the subpath prefix is available for computing
# STATIC_URL / MEDIA_URL but is NOT stored as settings.SCRIPT_NAME.
# allauth's AccountMiddleware checks settings.SCRIPT_NAME (and FORCE_SCRIPT_NAME)
# and raises a 400 if request.path doesn't start with it — but Nginx strips the
# subpath prefix before forwarding (proxy_pass trailing slash), so request.path
# is always '/', making that check fail. The WSGI wrapper in config/wsgi.py
# injects SCRIPT_NAME into the WSGI environ directly, which is how Django picks
# it up for URL generation without triggering allauth's validation.
_script_name = env('SCRIPT_NAME', default='/ARJournal')
STATIC_URL = f'{_script_name}/static/'
MEDIA_URL = f'{_script_name}/media/'

# ── Proxy / SSL ───────────────────────────────────────────────────────────────
# SSL is terminated at Nginx — the app receives plain HTTP from Gunicorn.
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Shorter HSTS for staging.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
