"""Re-ingest submissions: rebuild the stored CanonicalDocument from source.

The canonical JSON is produced by the LaTeX/WYSIWYG parser at ingest time and
then cached on CanonicalDocument. After a parser fix (e.g. title/table/abstract
rendering) existing submissions keep their old, broken JSON until re-ingested.
This command re-runs ingest_submission() for a submission's current revision,
which regenerates the canonical document in place (update_or_create).

    python manage.py reingest_submissions 15          # one submission by id
    python manage.py reingest_submissions 15 16 17     # several
    python manage.py reingest_submissions --all        # every submission
    python manage.py reingest_submissions --all --dry-run   # list, change nothing

It runs synchronously (no Celery broker needed), mirroring how the editorial
preview builds a canonical document on demand.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.submissions.models import Submission


class Command(BaseCommand):
    help = 'Rebuild stored CanonicalDocument(s) from source by re-running ingest.'

    def add_arguments(self, parser):
        parser.add_argument('submission_ids', nargs='*', type=int,
                            help='Submission id(s) to re-ingest.')
        parser.add_argument('--all', action='store_true',
                            help='Re-ingest every submission that has a current revision.')
        parser.add_argument('--dry-run', action='store_true',
                            help='List what would be re-ingested and exit without changes.')

    def handle(self, *args, **opts):
        from apps.production.tasks import ingest_submission

        ids = opts['submission_ids']
        if opts['all'] and ids:
            raise CommandError('Pass either submission ids or --all, not both.')
        if not opts['all'] and not ids:
            raise CommandError('Provide submission id(s) or --all.')

        qs = Submission.objects.all().order_by('pk')
        if ids:
            qs = qs.filter(pk__in=ids)
            found = set(qs.values_list('pk', flat=True))
            missing = [i for i in ids if i not in found]
            if missing:
                raise CommandError(f'No submission(s) with id: {missing}')

        total = qs.count()
        self.stdout.write(f'{total} submission(s) to re-ingest'
                          + (' (DRY RUN)' if opts['dry_run'] else '') + '.')

        ok = failed = skipped = 0
        for sub in qs:
            revision = sub.get_current_revision()
            label = f'#{sub.pk} "{(sub.title or "")[:50]}"'
            if revision is None:
                self.stdout.write(self.style.WARNING(f'  skip {label} — no current revision'))
                skipped += 1
                continue
            if opts['dry_run']:
                self.stdout.write(f'  would re-ingest {label} (revision {revision.pk})')
                continue
            try:
                result = ingest_submission(revision.pk)
            except Exception as e:  # noqa: BLE001 — report and continue with the rest
                self.stdout.write(self.style.ERROR(f'  FAIL {label} — {e}'))
                failed += 1
                continue
            if isinstance(result, dict) and result.get('error'):
                self.stdout.write(self.style.ERROR(f'  FAIL {label} — {result["error"]}'))
                failed += 1
            else:
                self.stdout.write(self.style.SUCCESS(f'  re-ingested {label}'))
                ok += 1

        if not opts['dry_run']:
            self.stdout.write(f'Done: {ok} re-ingested, {failed} failed, {skipped} skipped.')
