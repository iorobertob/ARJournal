"""
Turnitin Content Analysis (TCA) API v1 integration.
Enabled when settings.TURNITIN_ENABLED = True.

Workflow:
1. Accept EULA (once per user)
2. Create submission record
3. Upload manuscript content
4. Request similarity report
5. Poll/retrieve similarity score
"""
import requests
from django.conf import settings


BASE_URL = getattr(settings, 'TURNITIN_BASE_URL', 'https://api.turnitin.com')
API_KEY = getattr(settings, 'TURNITIN_API_KEY', '')

HEADERS = {
    'X-Turnitin-Integration-Name': 'Trans/Act Journal Platform',
    'X-Turnitin-Integration-Version': '1.0',
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
}


def _enabled():
    return getattr(settings, 'TURNITIN_ENABLED', False) and bool(API_KEY)


def check_eula_acceptance(owner_id: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    resp = requests.get(
        f'{BASE_URL}/api/v1/eula/latest/accept/{owner_id}',
        headers=HEADERS, timeout=15,
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
        f'{BASE_URL}/api/v1/submissions',
        json=payload, headers=HEADERS, timeout=15,
    )
    return resp.json()


def upload_content(submission_id: str, file_bytes: bytes, filename: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    headers = {
        **HEADERS,
        'Content-Type': 'binary/octet-stream',
        'Content-Disposition': f'inline; filename="{filename}"',
    }
    resp = requests.put(
        f'{BASE_URL}/api/v1/submissions/{submission_id}/original',
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
        f'{BASE_URL}/api/v1/submissions/{submission_id}/similarity',
        json=payload, headers=HEADERS, timeout=15,
    )
    return resp.json()


def get_similarity_report(submission_id: str) -> dict:
    if not _enabled():
        return {'status': 'disabled'}
    resp = requests.get(
        f'{BASE_URL}/api/v1/submissions/{submission_id}/similarity',
        headers=HEADERS, timeout=15,
    )
    return resp.json()


def run_full_check(revision) -> dict:
    """
    Convenience function: run the full Turnitin check pipeline for a revision.
    Stores result in SimilarityCheck model.
    """
    if not _enabled():
        return {'status': 'disabled', 'message': 'TURNITIN_ENABLED=False'}
    from apps.submissions.models import SimilarityCheck
    from django.utils import timezone

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
