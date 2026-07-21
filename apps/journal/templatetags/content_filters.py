"""Template filters for rendering editorial content that may be either legacy
plain text or WYSIWYG-authored HTML."""
import re

from django import template
from django.template.defaultfilters import linebreaks
from django.utils.safestring import mark_safe

register = template.Library()

# Detects HTML produced by the WYSIWYG editor (see static/js/wysiwyg.js).
_HTML_RE = re.compile(
    r'<(p|br|h[2-6]|ul|ol|li|strong|em|b|i|u|a|blockquote)\b', re.IGNORECASE
)


@register.filter
def richtext(value):
    """Render editorial content.

    New content is WYSIWYG HTML (already sanitized on save via
    ``apps.journal.sanitize.sanitize_html``) and is emitted as-is. Legacy
    plain-text content (no HTML tags) falls back to ``linebreaks`` so existing
    paragraph breaks are preserved and the text is escaped.
    """
    if not value:
        return ''
    if _HTML_RE.search(value):
        return mark_safe(value)
    return linebreaks(value)
