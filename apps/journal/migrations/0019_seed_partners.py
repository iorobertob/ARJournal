"""Seed the consortium partner institutions with their logos.

Idempotent: only runs when no Partner rows exist yet, so it never overwrites
partners an editor has added/edited through the dashboard (safe on production).
The logo files ship in static/img/partners/ and are copied into media storage
(local or S3) the first time this migration runs.
"""
import os

from django.contrib.staticfiles import finders
from django.core.files import File
from django.db import migrations


# (name, location, url, logo filename in static/img/partners/)
PARTNERS = [
    ('University of the Arts Helsinki', 'Research Institute, Finland',
     'https://www.uniarts.fi/en/', 'uniarts.svg'),
    ('Janáček Academy of Performing Arts', 'Czech Republic',
     'https://www.jamu.cz/en/', 'jamu.svg'),
    ('Lithuanian Academy of Music and Theatre', 'Lithuania',
     'https://lmta.lt/en', 'lmta.png'),
    ('ESMAE – i2ADS, Faculty of Performing Arts', 'Polytechnic of Porto, Portugal',
     'https://www.esmae.ipp.pt/', 'esmae.png'),
    ('Academy of Performing Arts in Bratislava', 'Slovakia',
     'https://www.vsmu.sk/', 'vsmu.svg'),
    ('Estonian Academy of Music and Theatre', 'Estonia',
     'https://eamt.ee/en/', 'eamt.svg'),
]


def seed(apps, schema_editor):
    Partner = apps.get_model('journal', 'Partner')
    if Partner.objects.exists():
        return
    for order, (name, location, url, filename) in enumerate(PARTNERS):
        partner = Partner(name=name, location=location, url=url, order=order, is_active=True)
        source = finders.find(f'img/partners/{filename}')
        if source and os.path.exists(source):
            with open(source, 'rb') as fh:
                partner.logo.save(filename, File(fh), save=False)
        partner.save()


def unseed(apps, schema_editor):
    # Non-destructive reverse: leave partner records in place.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0018_partner'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
