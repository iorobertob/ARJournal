"""Minimal allowlist HTML sanitizer (stdlib only — no external dependency).

Used to clean rich-text editorial content (About / Mission / Methodology /
Submission guidelines) authored via the WYSIWYG editor in Journal Settings
before it is stored and later rendered with `|safe` / the `richtext` filter.

Only a small, fixed set of formatting tags is allowed; everything else is
dropped (its text content is kept, except for <script>/<style> whose content is
discarded). The single permitted attribute is a scheme-checked `href` on <a>.
This is defence-in-depth: these fields are edited only by trusted journal
admins, but stored HTML rendered as-safe should never be able to carry script.
"""
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {
    'p', 'br', 'strong', 'b', 'em', 'i', 'u',
    'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'blockquote', 'a',
    # Tables — used by the Terms & Conditions page. Structure only; any inline
    # styling is dropped and supplied by the `.prose table` CSS instead.
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
}
VOID_TAGS = {'br'}
DROP_CONTENT_TAGS = {'script', 'style'}
ALLOWED_ATTRS = {
    'a': {'href', 'title'},
    'th': {'scope', 'colspan', 'rowspan'},
    'td': {'scope', 'colspan', 'rowspan'},
}
ALLOWED_SCHEMES = ('http:', 'https:', 'mailto:')


def _safe_href(value):
    """Return a safe href, or None to drop the attribute."""
    v = (value or '').strip()
    if not v or v.startswith('//'):          # empty or protocol-relative
        return None
    if v.lower().startswith(ALLOWED_SCHEMES):
        return v
    if v.startswith('/') or v.startswith('#'):   # site-relative / anchor
        return v
    first = v.split('/', 1)[0].split('?', 1)[0].split('#', 1)[0]
    if ':' not in first:                     # relative path, no scheme
        return v
    return None                              # anything with an unknown scheme


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self._drop_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth or tag not in ALLOWED_TAGS:
            return
        rendered = ''
        for k, v in attrs:
            if k in ALLOWED_ATTRS.get(tag, ()):
                if k == 'href':
                    href = _safe_href(v)
                    if href is None:
                        continue
                    rendered += ' href="%s"' % escape(href, quote=True)
                else:
                    rendered += ' %s="%s"' % (k, escape(v or '', quote=True))
        self.out.append('<%s%s>' % (tag, rendered))

    def handle_startendtag(self, tag, attrs):
        if not self._drop_depth and tag in ALLOWED_TAGS:
            self.out.append('<%s>' % tag)

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT_TAGS:
            self._drop_depth = max(0, self._drop_depth - 1)
            return
        if self._drop_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        self.out.append('</%s>' % tag)

    def handle_data(self, data):
        if not self._drop_depth:
            self.out.append(escape(data))

    def result(self):
        return ''.join(self.out).strip()


def sanitize_html(value):
    """Return `value` with only allowlisted tags/attributes kept."""
    if not value:
        return ''
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    html = parser.result()
    # Treat an editor left effectively empty as blank.
    if html in ('', '<p></p>', '<p><br></p>', '<br>'):
        return ''
    return html
