"""
XML sitemaps for the public journal site.

Google (and other crawlers) read /sitemap.xml to discover every published
article, issue and static page. Register it in Google Search Console.

Host handling: production is a root domain (https://inact.lmta.lt), but staging
can live under a subpath (e.g. https://misc.lmta.lt/journal). The Sitemap
framework normally builds URLs from
the django.contrib.sites domain (host only, no scheme, no subpath). We instead
derive the scheme + host from SITE_URL and let ``location()`` (via ``reverse``)
supply the path — which already includes the WSGI script-name prefix in prod —
so the emitted URLs are correct in every environment without depending on the
django_site DB row being set.
"""
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

_PARSED = urlparse(settings.SITE_URL)


class _SiteURLMixin:
    """Force the sitemap host/scheme to come from SITE_URL, not the Sites DB row."""
    protocol = _PARSED.scheme or 'https'

    def get_urls(self, page=1, site=None, protocol=None):
        class _Site:
            domain = _PARSED.netloc
            name = _PARSED.netloc
        return super().get_urls(page=page, site=_Site, protocol=self.protocol)


class ArticleSitemap(_SiteURLMixin, Sitemap):
    changefreq = 'monthly'
    priority = 0.9

    def items(self):
        from apps.production.models import HTMLBuild
        return (
            HTMLBuild.objects
            .filter(is_published=True)
            .order_by('-published_at')
        )

    def location(self, obj):
        return reverse('article_detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.published_at or obj.built_at


class IssueSitemap(_SiteURLMixin, Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        from apps.journal.models import Issue
        return Issue.objects.filter(is_published=True).order_by('-year', '-number')

    def location(self, obj):
        return reverse('issue_detail', args=[obj.number])


class StaticSitemap(_SiteURLMixin, Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return [
            'home', 'archive', 'about', 'editorial_board',
            'submit_info', 'partners', 'faq', 'terms', 'policy',
        ]

    def location(self, name):
        return reverse(name)


sitemaps = {
    'articles': ArticleSitemap,
    'issues': IssueSitemap,
    'static': StaticSitemap,
}
