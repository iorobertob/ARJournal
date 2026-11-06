"""Manage the account-purge allowlist (emails/domains the cleanup never deletes).

Permanent domain skips (e.g. lmta.lt) live in settings
(ACCOUNT_PURGE_PROTECTED_DOMAINS); this command manages the runtime DB allowlist
that is honored by both manual runs and the daily Celery beat run.

    python manage.py purge_allowlist list
    python manage.py purge_allowlist add alice@example.com --note "visiting editor"
    python manage.py purge_allowlist add example.org            # whole domain
    python manage.py purge_allowlist add @example.org           # whole domain
    python manage.py purge_allowlist remove alice@example.com
"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Add, remove, or list account-purge allowlist entries (emails/domains).'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['add', 'remove', 'list'])
        parser.add_argument('value', nargs='?', help='Email, domain, or @domain (for add/remove).')
        parser.add_argument('--note', default='', help='Optional note (add only).')

    def handle(self, *args, **options):
        from apps.accounts.models import PurgeExemption
        from django.conf import settings

        action = options['action']

        if action == 'list':
            domains = settings.ACCOUNT_PURGE_PROTECTED_DOMAINS or []
            emails = settings.ACCOUNT_PURGE_PROTECTED_EMAILS or []
            self.stdout.write('Permanent (settings) — cannot be removed via CLI:')
            for d in domains:
                self.stdout.write(f'  domain  {d}')
            for e in emails:
                self.stdout.write(f'  email   {e}')
            self.stdout.write('\nRuntime allowlist (DB):')
            entries = PurgeExemption.objects.all()
            if not entries:
                self.stdout.write('  (none)')
            for ex in entries:
                note = f'  — {ex.note}' if ex.note else ''
                self.stdout.write(f'  {ex.kind:7} {ex.value}{note}')
            return

        value = options.get('value')
        if not value:
            raise CommandError(f'`{action}` needs a value, e.g. alice@example.com or example.org')
        kind, norm = PurgeExemption.normalize(value)

        if action == 'add':
            obj, created = PurgeExemption.objects.get_or_create(
                value=norm, defaults={'kind': kind, 'note': options['note']})
            if not created:
                self.stdout.write(self.style.WARNING(
                    f'Already allowlisted: {obj.kind} {obj.value}'))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Added to allowlist: {kind} {norm}'
                    f'{" — " + options["note"] if options["note"] else ""}'))
        elif action == 'remove':
            deleted, _ = PurgeExemption.objects.filter(value=norm).delete()
            if deleted:
                self.stdout.write(self.style.SUCCESS(f'Removed from allowlist: {norm}'))
            else:
                self.stdout.write(self.style.WARNING(
                    f'Not in the runtime allowlist: {norm} '
                    f'(settings-level entries like lmta.lt are permanent and not removable here)'))
