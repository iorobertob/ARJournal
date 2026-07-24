"""Template filters for rendering editorial content that may be either legacy
plain text or WYSIWYG-authored HTML."""
import re

from django import template
from django.template.defaultfilters import linebreaks
from django.utils.safestring import mark_safe

register = template.Library()

# Detects HTML produced by the WYSIWYG editor (see static/js/wysiwyg.js).
_HTML_RE = re.compile(
    r'<(p|br|h[2-6]|ul|ol|li|strong|em|b|i|u|a|blockquote|table)\b', re.IGNORECASE
)

# Opening <a> tags whose href is external (http/https/mailto) and that don't
# already declare a target — used to make external links open in a new tab,
# matching the behaviour of the article renderer (html_renderer._render_inline).
_EXT_A_RE = re.compile(
    r'<a\s+(?![^>]*\btarget=)([^>]*?href=(["\'])(?:https?:|mailto:)[^>]*?)>',
    re.IGNORECASE,
)


def _external_links_new_tab(html):
    return _EXT_A_RE.sub(
        lambda m: '<a %s target="_blank" rel="noopener noreferrer">' % m.group(1),
        html,
    )


@register.filter
def richtext(value):
    """Render editorial content.

    New content is WYSIWYG HTML (already sanitized on save via
    ``apps.journal.sanitize.sanitize_html``) and is emitted as-is, except that
    external links are given ``target="_blank"`` so they open in a new tab.
    Legacy plain-text content (no HTML tags) falls back to ``linebreaks`` so
    existing paragraph breaks are preserved and the text is escaped.
    """
    if not value:
        return ''
    if _HTML_RE.search(value):
        return mark_safe(_external_links_new_tab(value))
    return linebreaks(value)
