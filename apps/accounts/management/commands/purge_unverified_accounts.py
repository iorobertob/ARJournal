"""Delete abandoned unverified self-signup accounts (bot/spam cleanup).

Runs daily via Celery beat; this command is for manual/ad-hoc runs and dry-runs.
A dry run lists exactly which accounts would be deleted (id, email, join date)
without touching anything. A real run deletes them and records an AuditEvent
(event_type "account_purged") plus a logger line for each.

    python manage.py purge_unverified_accounts --dry-run
    python manage.py purge_unverified_accounts --days 7
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Delete abandoned unverified self-signup accounts older than N days.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,
                            help='Minimum account age in days (default: 7).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Report the count without deleting anything.')

    def handle(self, *args, **options):
        from apps.notifications.tasks import purge_unverified_accounts
        days = options['days']
        dry_run = options['dry_run']
        affected = purge_unverified_accounts(
            days=days, dry_run=dry_run, trigger='manual',
        )
        count = len(affected)
        verb = 'Would delete' if dry_run else 'Deleted'

        if affected:
            self.stdout.write(f'{verb} the following account(s):')
            for a in affected:
                self.stdout.write(f"  #{a['id']}  {a['email']}  (joined {a['date_joined']})")

        self.stdout.write(self.style.SUCCESS(
            f'{verb} {count} unverified account(s) older than {days} day(s).'
        ))
        if not dry_run and count:
            self.stdout.write(
                'Each deletion was recorded as an AuditEvent (event_type="account_purged").'
            )
