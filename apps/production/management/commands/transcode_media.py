"""Backfill: transcode existing video/audio assets to protected HLS.

Video and audio uploaded before streaming was enabled have no HLS package yet
(so they fall back to the signed progressive stream). Run this once to generate
their HLS ladders:

    python manage.py transcode_media            # inline, only assets not ready
    python manage.py transcode_media --async    # queue on the transcode worker
    python manage.py transcode_media --all       # re-transcode everything
"""
from django.core.management.base import BaseCommand

from apps.submissions.models import SubmissionAsset


class Command(BaseCommand):
    help = 'Transcode existing video/audio assets to HLS.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true',
                            help='Re-transcode even assets already marked ready.')
        parser.add_argument('--async', action='store_true', dest='async_',
                            help='Queue via the transcode Celery worker instead of running inline.')

    def handle(self, *args, **opts):
        from apps.production.tasks import transcode_asset

        qs = SubmissionAsset.objects.filter(kind__in=['video', 'audio']).order_by('pk')
        if not opts['all']:
            qs = qs.exclude(hls_status=SubmissionAsset.HLS_READY)

        total = qs.count()
        self.stdout.write(f'{total} video/audio asset(s) to transcode.')
        for asset in qs:
            label = f'#{asset.pk} {asset.original_filename} ({asset.kind})'
            if opts['async_']:
                transcode_asset.delay(asset.pk)
                self.stdout.write(f'  queued {label}')
            else:
                self.stdout.write(f'  transcoding {label} …')
                result = transcode_asset(asset.pk)
                self.stdout.write(self.style.SUCCESS(f'    → {result}'))
        self.stdout.write(self.style.SUCCESS('Done.'))
