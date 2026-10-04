"""Template filters for rendering editorial content that may be either legacy
plain text or WYSIWYG-authored HTML."""
import re
from django.utils.html import escape

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

# Matches {{token_name}} placeholders written in WYSIWYG content.
_TOKEN_RE = re.compile(r'\{\{(\w+)\}\}')

# Tokens that resolve to email addresses are rendered as mailto links.
_EMAIL_TOKENS = {'editorial_email', 'contact_email'}

# All supported tokens → JournalConfig attribute name (same string in this case).
JOURNAL_TOKENS = {
    'editorial_email',
    'contact_email',
    'journal_name',
    'institution',
    'publisher',
    'issn_print',
    'issn_online',
    'tagline',
}


def _get_token_map():
    from apps.journal.models import JournalConfig
    cfg = JournalConfig.get()
    return {
        'editorial_email': cfg.editorial_email,
        'contact_email':   cfg.contact_email,
        'journal_name':    cfg.name,
        'institution':     cfg.institution,
        'publisher':       cfg.publisher,
        'issn_print':      cfg.issn_print,
        'issn_online':     cfg.issn_online,
        'tagline':         cfg.tagline,
    }


def _expand_tokens(html):
    """Replace {{token}} placeholders with live JournalConfig values."""
    tokens = _get_token_map()

    def replace(m):
        key = m.group(1)
        value = tokens.get(key)
        if not value:
            return m.group(0)  # unknown or empty — leave as-is
        safe_value = escape(value)
        if key in _EMAIL_TOKENS:
            return '<a href="mailto:{v}">{v}</a>'.format(v=safe_value)
        return safe_value

    return _TOKEN_RE.sub(replace, html)


def _external_links_new_tab(html):
    return _EXT_A_RE.sub(
        lambda m: '<a %s target="_blank" rel="noopener noreferrer">' % m.group(1),
        html,
    )


@register.filter
def richtext(value):
    """Render editorial content.

    New content is WYSIWYG HTML (already sanitized on save via
    ``apps.journal.sanitize.sanitize_html``) and is emitted as-is, except that:
    - {{token}} placeholders are expanded to live JournalConfig values.
    - External links are given ``target="_blank"`` so they open in a new tab.
    Legacy plain-text content (no HTML tags) falls back to ``linebreaks`` so
    existing paragraph breaks are preserved and the text is escaped.
    """
    if not value:
        return ''
    if _HTML_RE.search(value):
        return mark_safe(_external_links_new_tab(_expand_tokens(value)))
    # Plain text: expand tokens before escaping via linebreaks isn't possible,
    # so just expand and then linebreaks (tokens produce safe HTML).
    expanded = _expand_tokens(value)
    if _HTML_RE.search(expanded):
        return mark_safe(_external_links_new_tab(expanded))
    return linebreaks(expanded)
