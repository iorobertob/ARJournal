"""
Staging settings — app served at a subpath on a shared server
(e.g. https://misc.lmta.lt/ARJournal).

Extends production settings and overrides what changes for subpath deployment.
Set SCRIPT_NAME in .env to the subpath (e.g. SCRIPT_NAME=/ARJournal).

How the subpath proxy works:
  Nginx receives:  GET /ARJournal/articles/
  proxy_pass (with trailing slash) strips the prefix, forwards: GET /articles/
  Django sees /articles/ — matches URL patterns normally.
  FORCE_SCRIPT_NAME tells Django to prefix all generated URLs so that links,
  redirects, and form actions resolve correctly in the browser.
"""
from .production import *  # noqa: F401, F403

# ── Subpath configuration ─────────────────────────────────────────────────────
# Read SCRIPT_NAME from .env (e.g. SCRIPT_NAME=/ARJournal)
# The value must start with / and have no trailing slash.
SCRIPT_NAME = env('SCRIPT_NAME', default='/journal')
FORCE_SCRIPT_NAME = SCRIPT_NAME

# Static and media URLs must include the subpath so Nginx can route them to
# the correct alias and serve them directly from disk.
STATIC_URL = f'{SCRIPT_NAME}/static/'
MEDIA_URL = f'{SCRIPT_NAME}/media/'

# ── Proxy / SSL ───────────────────────────────────────────────────────────────
# SSL is terminated at Nginx — don't redirect again inside the app.
SECURE_SSL_REDIRECT = False
# Tell Django the original request was HTTPS (Nginx sets X-Forwarded-Proto).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Shorter HSTS for staging — easy to roll back if something goes wrong.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
