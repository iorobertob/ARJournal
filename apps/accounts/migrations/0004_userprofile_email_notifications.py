from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_managers'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_notifications',
            field=models.BooleanField(default=True),
        ),
    ]
