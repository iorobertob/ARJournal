"""Development-only static files storage.

Appends a ``?v=<mtime>`` query string to every ``{% static %}`` URL, keyed on
the source file's modification time. The URL changes the moment a static file
is edited, so the browser fetches the fresh copy on an ordinary reload — no more
hard refresh (Ctrl/Cmd+Shift+R) to see CSS/JS changes.

Only wired up in ``config.settings.development``. Production uses WhiteNoise's
``CompressedManifestStaticFilesStorage``, which hashes filenames and already
busts caches on deploy.
"""
import os

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class CacheBustingStaticFilesStorage(StaticFilesStorage):
    def url(self, name):
        url = super().url(name)
        abs_path = finders.find(name)
        if abs_path:
            try:
                mtime = int(os.path.getmtime(abs_path))
            except OSError:
                return url
            sep = '&' if '?' in url else '?'
            url = f'{url}{sep}v={mtime}'
        return url
