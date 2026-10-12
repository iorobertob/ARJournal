"""Recolour the Estonian Academy (EAMT) partner logo from blue to black.

The EAMT logo was seeded (migration 0019) in its brand blue (#102694) while
every other partner logo is black. The repo's static source is now black; this
migration updates environments where the blue file was already seeded.

Safe / non-destructive:
- Only touches the partner whose logo is still the *exact* original seed path
  ('partners/eamt.svg'); an admin re-upload always gets a different filename, so
  a customised logo is never overwritten.
- Saves the black file under a fresh name, which also busts the media cache.
- A no-op if the partner/file is absent (e.g. partners not seeded here yet —
  the fresh seed already produces the black version).
"""
import os

from django.contrib.staticfiles import finders
from django.core.files import File
from django.db import migrations

ORIGINAL_SEED_NAME = 'partners/eamt.svg'


def recolor(apps, schema_editor):
    Partner = apps.get_model('journal', 'Partner')
    try:
        partner = Partner.objects.get(logo=ORIGINAL_SEED_NAME)
    except (Partner.DoesNotExist, Partner.MultipleObjectsReturned):
        return
    source = finders.find('img/partners/eamt.svg')
    if not source or not os.path.exists(source):
        return
    storage = partner.logo.storage
    old_name = partner.logo.name  # capture as a string BEFORE .save() rebinds it
    with open(source, 'rb') as fh:
        partner.logo.save('eamt.svg', File(fh), save=False)  # gets a unique name
    partner.save(update_fields=['logo'])
    # Remove the old (blue) file by name, now that the record points elsewhere.
    if old_name and old_name != partner.logo.name and storage.exists(old_name):
        try:
            storage.delete(old_name)
        except Exception:
            pass


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0019_seed_partners'),
    ]

    operations = [
        migrations.RunPython(recolor, noop),
    ]
