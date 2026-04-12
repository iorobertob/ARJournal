"""
Crossref DOI deposit integration.
Enabled when JournalConfig.doi_enabled = True.
"""
import requests


def _cfg():
    from apps.journal.models import JournalConfig
    return JournalConfig.get()


def deposit_doi(document, doi_suffix: str) -> dict:
    """
    Build CrossRef XML and deposit a DOI.
    Returns {'status': 'deposited', 'doi': ..., 'response': ...}
    """
    cfg = _cfg()
    if not cfg.doi_enabled:
        return {'status': 'disabled', 'message': 'DOI not enabled in Journal Settings'}

    meta = document.data.get('metadata', {})
    title = meta.get('title', {}).get('main', '')
    contributors = document.data.get('contributors', [])
    submission = document.revision.submission

    prefix = cfg.doi_prefix or '10.XXXXX'
    doi = f'{prefix}/{doi_suffix}'

    # Minimal CrossRef schema 5.3 XML
    xml = _build_crossref_xml(title, contributors, doi, submission)

    url = 'https://doi.crossref.org/servlet/deposit'
    try:
        resp = requests.post(
            url,
            data={
                'login_id': cfg.crossref_login,
                'login_passwd': cfg.crossref_password,
            },
            files={'fname': ('deposit.xml', xml.encode('utf-8'), 'text/xml')},
            timeout=30,
        )
        resp.raise_for_status()
        from apps.production.models import DOIDeposit
        deposit, _ = DOIDeposit.objects.get_or_create(document=document)
        deposit.doi = doi
        deposit.status = 'deposited'
        deposit.crossref_response = {'status_code': resp.status_code, 'text': resp.text[:500]}
        from django.utils import timezone
        deposit.deposited_at = timezone.now()
        deposit.save()
        return {'status': 'deposited', 'doi': doi}
    except requests.RequestException as e:
        return {'status': 'failed', 'error': str(e)}


def _build_crossref_xml(title: str, contributors: list, doi: str, submission) -> str:
    cfg = _cfg()
    depositor_name = cfg.crossref_depositor_name
    depositor_email = cfg.crossref_depositor_email
    year = submission.issue.year if submission.issue else 2026
    contributors_xml = ''
    for i, c in enumerate(contributors):
        role = 'first' if i == 0 else 'additional'
        name_parts = c.get('displayName', '').split(' ', 1)
        given = name_parts[0] if name_parts else ''
        family = name_parts[1] if len(name_parts) > 1 else given
        contributors_xml += (
            f'<person_name sequence="{role}" contributor_role="author">'
            f'<given_name>{given}</given_name>'
            f'<surname>{family}</surname>'
            f'</person_name>'
        )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<doi_batch version="5.3" xmlns="http://www.crossref.org/schema/5.3.0">
  <head>
    <depositor><depositor_name>{depositor_name}</depositor_name><email_address>{depositor_email}</email_address></depositor>
  </head>
  <body>
    <journal>
      <journal_article>
        <titles><title>{title}</title></titles>
        <contributors>{contributors_xml}</contributors>
        <publication_date><year>{year}</year></publication_date>
        <doi_data><doi>{doi}</doi><resource>https://trans-act-journal.org/articles/{doi.split("/")[-1]}/</resource></doi_data>
      </journal_article>
    </journal>
  </body>
</doi_batch>'''
