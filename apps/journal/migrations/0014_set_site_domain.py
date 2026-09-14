"""
Point the django.contrib.sites Site (SITE_ID=1) at the deployment's real host,
derived from SITE_URL. The default row is 'example.com', which leaks into any
absolute URL built via the Sites framework (e.g. allauth account emails).

Runs per-environment: on production it sets inact.lmta.lt; in dev, localhost.
"""
from urllib.parse import urlparse

from django.conf import settings
from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    netloc = urlparse(settings.SITE_URL).netloc or 'localhost'
    site_id = getattr(settings, 'SITE_ID', 1)
    Site.objects.update_or_create(
        pk=site_id,
        defaults={'domain': netloc, 'name': netloc},
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('journal', '0013_seed_faq'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(set_site_domain, noop),
    ]
