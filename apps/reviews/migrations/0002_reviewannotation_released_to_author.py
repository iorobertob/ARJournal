from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewannotation',
            name='released_to_author',
            field=models.BooleanField(default=False),
        ),
    ]
