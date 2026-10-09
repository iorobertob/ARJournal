"""Project-wide HTTP middleware."""


class HTMLNoCacheMiddleware:
    """Make browsers revalidate HTML pages on every navigation.

    Static assets are content-hashed (``ManifestStaticFilesStorage``) and cached
    "forever", so the only thing that tells a browser about new asset URLs after
    a deploy is the HTML itself. If a browser serves a *cached* HTML page it will
    keep referencing the old hashed CSS/JS until that page revalidates — the
    classic "I deployed but users still see the old styles until a hard refresh".

    Marking HTML ``no-cache`` closes that gap: the page may be stored but must be
    revalidated with the server before use, so a returning visitor always gets
    the current HTML (and therefore the current hashed assets). Hashed static
    files keep their long/immutable cache — only the HTML shell is revalidated.

    Scope is deliberately narrow:
    - only ``text/html`` responses are touched (never static files, media,
      streaming, JSON/API, downloads);
    - responses that already carry a ``Cache-Control`` header are left alone, so
      ``@never_cache`` views and anything that sets its own caching still win.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not response.has_header('Cache-Control'):
            content_type = response.get('Content-Type', '')
            if content_type.startswith('text/html'):
                response['Cache-Control'] = 'no-cache'
        return response
