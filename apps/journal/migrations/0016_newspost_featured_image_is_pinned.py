from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0015_alter_journalconfig_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='newspost',
            old_name='thumbnail',
            new_name='featured_image',
        ),
        migrations.AddField(
            model_name='newspost',
            name='is_pinned',
            field=models.BooleanField(
                default=False,
                help_text='Pin this post to the homepage. Only one post can be pinned at a time.',
            ),
        ),
    ]
