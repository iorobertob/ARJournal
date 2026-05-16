from django import template
from django.utils.html import format_html
from django.utils.timezone import is_aware
from django.utils.formats import date_format

register = template.Library()


@register.filter
def local_dt(value):
    """Render a datetime as a <time> element that JS will convert to the
    viewer's local timezone. Falls back to UTC if JS is unavailable."""
    if not value:
        return '—'
    iso = value.isoformat() if is_aware(value) else value.strftime('%Y-%m-%dT%H:%M:%S+00:00')
    fallback = date_format(value, 'j N Y, H:i')
    return format_html(
        '<time class="local-dt" datetime="{}">{}</time>',
        iso,
        fallback,
    )
