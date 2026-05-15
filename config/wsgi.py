import os
from urllib.parse import urlparse
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

_django_app = get_wsgi_application()

# Subpath deployment: derive SCRIPT_NAME from SITE_URL's path component.
#
# SITE_URL=https://misc.lmta.lt/ARJournal  →  SCRIPT_NAME=/ARJournal
# SITE_URL=https://some-domain.com         →  SCRIPT_NAME='' (no injection)
#
# Nginx strips the subpath prefix before forwarding (proxy_pass trailing slash),
# so PATH_INFO arrives as '/' and Gunicorn's own SCRIPT_NAME validation would
# 400 every request. We pop it from os.environ (clearing Gunicorn's view) and
# inject it per-request into the WSGI environ ourselves instead.
_script_name = os.environ.pop('SCRIPT_NAME', '').rstrip('/')
if not _script_name:
    _script_name = urlparse(os.environ.get('SITE_URL', '')).path.rstrip('/')

if _script_name:
    def application(environ, start_response):
        environ['SCRIPT_NAME'] = _script_name
        return _django_app(environ, start_response)
else:
    application = _django_app
