import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

_django_app = get_wsgi_application()

# Subpath deployment support (Stage 1: misc.lmta.lt/ARJournal or similar).
#
# When the app is mounted at a URL subpath, Nginx strips the prefix before
# forwarding to Gunicorn (proxy_pass with trailing slash), so Django's
# PATH_INFO is '/' instead of '/ARJournal/...'. Setting SCRIPT_NAME in the
# WSGI environ tells Django what prefix to add when generating URLs.
#
# We do NOT use settings.FORCE_SCRIPT_NAME for this because allauth's
# AccountMiddleware validates that request.path starts with FORCE_SCRIPT_NAME —
# a check that fails when Nginx has already stripped the prefix.
#
# Set SCRIPT_NAME=/ARJournal (or your subpath) in .env.
# django-environ's read_env() (called during settings load above) writes it
# into os.environ, so it's available here immediately after get_wsgi_application().
#
_script_name = os.environ.get('SCRIPT_NAME', '').rstrip('/')

if _script_name:
    def application(environ, start_response):
        environ['SCRIPT_NAME'] = _script_name
        return _django_app(environ, start_response)
else:
    application = _django_app
