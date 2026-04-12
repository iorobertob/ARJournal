from django.db import migrations, models


def migrate_role_to_roles(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        old_role = user.role if hasattr(user, 'role') else None
        if old_role:
            user.roles = [old_role]
        else:
            user.roles = ['author']
        user.save(update_fields=['roles'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        # 1. Add the new field alongside the old one
        migrations.AddField(
            model_name='user',
            name='roles',
            field=models.JSONField(blank=True, default=list),
        ),
        # 2. Copy existing role → roles
        migrations.RunPython(migrate_role_to_roles, migrations.RunPython.noop),
        # 3. Remove the old field
        migrations.RemoveField(
            model_name='user',
            name='role',
        ),
    ]
