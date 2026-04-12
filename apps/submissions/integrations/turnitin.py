"""
Turnitin Content Analysis (TCA) API v1 integration.
Enabled when JournalConfig.turnitin_enabled = True.

Workflow:
1. Accept EULA (once per user)
2. Create submission record
3. Upload manuscript content
4. Request similarity report
5. Poll/retrieve similarity score
"""
import requests


def _cfg():
    from apps.journal.models import JournalConfig
    return JournalConfig.get()


def _enabled():
    cfg = _cfg()
    return cfg.turnitin_enabled and bool(cfg.turnitin_api_key)


def _headers():
    cfg = _cfg()
    return {
        'X-Turnitin-Integration-Name': 'Trans/Act Journal Platform',
        'X-Turnitin-Integration-Version': '1.0',
        'Authorization': f'Bearer {cfg.turnitin_api_key}',
        'Content-Type': 'application/json',
    }


def _base_url():
    return _cfg().turnitin_base_url or 'https://api.turnitin.com'


def check_eula_acceptance(owner_id: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    resp = requests.get(
        f'{_base_url()}/api/v1/eula/latest/accept/{owner_id}',
        headers=_headers(), timeout=15,
    )
    return resp.json()


def create_submission(owner_id: str, title: str, submitter_email: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    payload = {
        'owner': owner_id,
        'title': title,
        'submitter': submitter_email,
        'owner_default_permission_set': 'INSTRUCTOR',
        'submitter_default_permission_set': 'LEARNER',
        'extract_text_only': False,
    }
    resp = requests.post(
        f'{_base_url()}/api/v1/submissions',
        json=payload, headers=_headers(), timeout=15,
    )
    return resp.json()


def upload_content(submission_id: str, file_bytes: bytes, filename: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    headers = {
        **_headers(),
        'Content-Type': 'binary/octet-stream',
        'Content-Disposition': f'inline; filename="{filename}"',
    }
    resp = requests.put(
        f'{_base_url()}/api/v1/submissions/{submission_id}/original',
        data=file_bytes, headers=headers, timeout=60,
    )
    return resp.json()


def request_similarity_report(submission_id: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    payload = {
        'indexing_settings': {'add_to_index': False},
        'generation_settings': {
            'search_repositories': ['INTERNET', 'PUBLICATION', 'SUBMITTED_WORK'],
            'auto_exclude_self_matching_scope': 'ALL',
        },
    }
    resp = requests.put(
        f'{_base_url()}/api/v1/submissions/{submission_id}/similarity',
        json=payload, headers=_headers(), timeout=15,
    )
    return resp.json()


def get_similarity_report(submission_id: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    resp = requests.get(
        f'{_base_url()}/api/v1/submissions/{submission_id}/similarity',
        headers=_headers(), timeout=15,
    )
    return resp.json()


def run_full_check(revision) -> dict:
    """
    Convenience function: run the full Turnitin check pipeline for a revision.
    Stores result in SimilarityCheck model.
    """
    if not _enabled():
        return {'status': 'disabled', 'message': 'Turnitin not enabled in Journal Settings'}
    from apps.submissions.models import SimilarityCheck

    check, _ = SimilarityCheck.objects.get_or_create(revision=revision)
    check.status = 'processing'
    check.save()

    sub = revision.submission
    owner_id = str(sub.author.pk)
    turnitin_sub = create_submission(owner_id, sub.title, sub.author.email)
    tid = turnitin_sub.get('id')
    if not tid:
        check.status = 'error'
        check.raw_response = turnitin_sub
        check.save()
        return {'status': 'error', 'response': turnitin_sub}

    check.provider_submission_id = tid
    check.save()
    try:
        with revision.manuscript_file.open('rb') as f:
            content = f.read()
        upload_content(tid, content, revision.manuscript_file.name)
        request_similarity_report(tid)
        check.status = 'processing'
        check.save()
    except Exception as e:
        check.status = 'error'
        check.raw_response = {'error': str(e)}
        check.save()
    return {'status': 'processing', 'submission_id': tid}
