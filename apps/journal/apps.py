from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_site(sender, **kwargs):
    from django.conf import settings
    from urllib.parse import urlparse
    try:
        from django.contrib.sites.models import Site
        domain = urlparse(getattr(settings, 'SITE_URL', '')).netloc or 'localhost'
        Site.objects.update_or_create(
            pk=getattr(settings, 'SITE_ID', 1),
            defaults={'domain': domain, 'name': 'IN/ACT'},
        )
    except Exception:
        pass


class JournalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.journal'

    def ready(self):
        post_migrate.connect(_sync_site, sender=self)
