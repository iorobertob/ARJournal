"""Add EmailLog.created_at so every log (including failed sends) has a date.

Existing rows get created_at = sent_at where known, else the migration time.
"""
import django.utils.timezone
from django.db import migrations, models


def backfill_created_at(apps, schema_editor):
    EmailLog = apps.get_model('notifications', 'EmailLog')
    # For already-sent rows the send time is the best available creation date.
    EmailLog.objects.filter(sent_at__isnull=False).update(
        created_at=models.F('sent_at')
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0003_email_log_tracking'),
    ]

    operations = [
        migrations.AddField(
            model_name='emaillog',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_created_at, noop),
        migrations.AlterModelOptions(
            name='emaillog',
            options={'ordering': ['-created_at', '-id']},
        ),
    ]
