import uuid
from django.db import migrations, models


def populate_tracking_tokens(apps, schema_editor):
    EmailLog = apps.get_model('notifications', 'EmailLog')
    for log in EmailLog.objects.filter(tracking_token__isnull=True):
        log.tracking_token = uuid.uuid4()
        log.save(update_fields=['tracking_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_alter_notification_notification_type'),
    ]

    operations = [
        # Add all plain fields first
        migrations.AddField(
            model_name='emaillog',
            name='plain_body',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='emaillog',
            name='html_body',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='emaillog',
            name='opened_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='emaillog',
            name='opened_count',
            field=models.IntegerField(default=0),
        ),
        # Add tracking_token as nullable first so existing rows don't conflict
        migrations.AddField(
            model_name='emaillog',
            name='tracking_token',
            field=models.UUIDField(null=True, blank=True),
        ),
        # Populate tokens for any existing rows
        migrations.RunPython(populate_tracking_tokens, migrations.RunPython.noop),
        # Now enforce unique + non-null
        migrations.AlterField(
            model_name='emaillog',
            name='tracking_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        migrations.AlterModelOptions(
            name='emaillog',
            options={'ordering': ['-sent_at', '-id']},
        ),
    ]
