from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='journalconfig',
            name='email_from_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='email_from_address',
            field=models.EmailField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='mailersend_api_token',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='orcid_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='orcid_client_id',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='orcid_client_secret',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='doi_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='doi_prefix',
            field=models.CharField(blank=True, default='', help_text='e.g. 10.12345', max_length=50),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='crossref_login',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='crossref_password',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='crossref_depositor_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='crossref_depositor_email',
            field=models.EmailField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='turnitin_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='turnitin_api_key',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='turnitin_base_url',
            field=models.CharField(blank=True, default='https://api.turnitin.com', max_length=255),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='ai_features_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='journalconfig',
            name='openai_api_key',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
