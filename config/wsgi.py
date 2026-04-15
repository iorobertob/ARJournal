import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

_django_app = get_wsgi_application()

# Subpath deployment support (Stage 1: misc.lmta.lt/ARJournal or similar).
#
# When the app is mounted at a URL subpath, Nginx strips the prefix before
# forwarding to Gunicorn (proxy_pass with trailing slash), so Django's
# PATH_INFO is '/' instead of '/ARJournal/...'. We inject SCRIPT_NAME into
# the WSGI environ per-request so Django uses it for URL generation.
#
# IMPORTANT: Gunicorn also reads os.environ['SCRIPT_NAME'] (gunicorn/http/wsgi.py
# line 118) and validates that the request path starts with it. Since Nginx has
# already stripped the prefix, paths arrive as '/' and Gunicorn's own check
# fires with a 400. To prevent this, we pop SCRIPT_NAME from os.environ right
# here — django-environ's read_env() (called inside get_wsgi_application above)
# will have set it from .env. We keep the value in a local variable and inject
# it ourselves per-request below, bypassing Gunicorn's check entirely.
#
# Set SCRIPT_NAME=/ARJournal (or your subpath) in .env.
_script_name = os.environ.pop('SCRIPT_NAME', '').rstrip('/')

if _script_name:
    def application(environ, start_response):
        environ['SCRIPT_NAME'] = _script_name
        return _django_app(environ, start_response)
else:
    application = _django_app
