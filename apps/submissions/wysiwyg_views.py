import copy
import json
import re
import bibtexparser
from bibtexparser.bparser import BibTexParser

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Submission, SubmissionRevision, SubmissionStatus, RevisionSource
from .views import _upsert_asset, _copy_assets, _RESUBMITTABLE


@login_required
def wysiwyg_editor(request, pk):
    """Step 2 (WYSIWYG branch): render the TipTap editor."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)

    rev, _ = SubmissionRevision.objects.get_or_create(
        submission=sub,
        version=1,
        defaults={'source_type': RevisionSource.WYSIWYG},
    )
    # If an existing revision was created via LaTeX, don't hijack it.
    if rev.source_type == RevisionSource.LATEX and not rev.wysiwyg_data:
        rev.source_type = RevisionSource.WYSIWYG
        rev.save(update_fields=['source_type'])

    import json as _json
    from apps.journal.models import ArticleType
    wysiwyg_json = _json.dumps(rev.wysiwyg_data) if rev.wysiwyg_data else 'null'

    return render(request, 'author/submit_step2_wysiwyg.html', {
        'submission': sub,
        'revision': rev,
        'wysiwyg_json': wysiwyg_json,
        'article_types': ArticleType.choices,
        'is_resubmission': False,
        'continue_url': reverse('submission_step4', args=[sub.pk, rev.pk]),
    })


@login_required
@require_http_methods(['PATCH'])
def wysiwyg_metadata_save(request, pk):
    """Auto-save article metadata fields from the inline editor panel."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    fields = []
    if 'title' in payload and payload['title'].strip():
        sub.title = payload['title'].strip()
        fields.append('title')
    if 'subtitle' in payload:
        sub.subtitle = payload['subtitle'].strip()
        fields.append('subtitle')
    if 'article_type' in payload:
        sub.article_type = payload['article_type']
        fields.append('article_type')
    if 'abstract' in payload:
        sub.abstract = payload['abstract'].strip()
        fields.append('abstract')
    if 'keywords' in payload:
        raw = payload['keywords']
        sub.keywords = [k.strip() for k in raw.replace(';', ',').split(',') if k.strip()]
        fields.append('keywords')

    if fields:
        sub.save(update_fields=fields + ['updated_at'])

    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['PATCH'])
def wysiwyg_autosave(request, pk, rev):
    """Auto-save endpoint: persist wysiwyg_data JSON to the revision."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    revision.wysiwyg_data = {
        'content': payload.get('content', []),
        'bibliography': payload.get('bibliography', []),
    }
    revision.save(update_fields=['wysiwyg_data'])
    return JsonResponse({'status': 'ok'})


@login_required
@require_http_methods(['POST'])
def wysiwyg_asset_upload(request, pk, rev):
    """Upload a single file asset from the editor and return its metadata."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub)

    uploaded = request.FILES.get('file')
    if not uploaded:
        return JsonResponse({'error': 'No file provided'}, status=400)

    asset = _upsert_asset(revision, uploaded)

    return JsonResponse({
        'asset_id': f'asset_{asset.kind}_{asset.pk:03d}',
        'original_filename': asset.original_filename,
        'kind': asset.kind,
        'url': asset.file.url if asset.file else '',
        'asset_pk': asset.pk,
    })


@login_required
@require_http_methods(['POST'])
def wysiwyg_bibtex_import(request, pk):
    """Parse an uploaded .bib file and return structured citation items."""
    get_object_or_404(Submission, pk=pk, author=request.user)

    bib_file = request.FILES.get('file')
    if not bib_file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    raw = bib_file.read().decode('utf-8', errors='replace')

    def _clean(value):
        """Remove BibTeX capitalization-protection braces and trim whitespace."""
        return re.sub(r'[{}]', '', value or '').strip()

    parser = BibTexParser(common_strings=True)
    db = bibtexparser.loads(raw, parser=parser)

    items = []
    for entry in db.entries:
        authors_raw = _clean(entry.get('author', ''))
        authors = [a.strip() for a in authors_raw.replace('\n', ' ').split(' and ') if a.strip()]

        items.append({
            'citeKey': entry.get('ID', ''),
            'type': entry.get('ENTRYTYPE', 'misc'),
            'title': _clean(entry.get('title', '')),
            'authors': authors,
            'year': _clean(entry.get('year', '')),
            'journal': _clean(entry.get('journal', '')),
            'volume': _clean(entry.get('volume', '')),
            'number': _clean(entry.get('number', '')),
            'pages': _clean(entry.get('pages', '')),
            'publisher': _clean(entry.get('publisher', '')),
            'booktitle': _clean(entry.get('booktitle', '')),
            'editor': _clean(entry.get('editor', '')),
            'school': _clean(entry.get('school', '')),
            'doi': _clean(entry.get('doi', '')),
            'url': _clean(entry.get('url', '')),
        })

    return JsonResponse({'items': items})


# ── WYSIWYG resubmission ──────────────────────────────────────────────────────
#
# When a manuscript that was written in the online editor is sent back to the
# author — either as a post-review revision (REVISION_REQUESTED) or a
# post-screening correction (returned to author) — the author edits it in the
# same editor rather than uploading a replacement .tex file. The previous
# revision's content and assets are cloned into a fresh draft so nothing is lost.


def _resubmit_mode(sub):
    """Return the kind of resubmission the submission is currently open for, or
    None if it isn't open for one. 'review' → post-decision revision;
    'screening' → post-screening technical correction."""
    if sub.status in _RESUBMITTABLE:
        return 'review'
    if sub.is_returned_to_author:
        return 'screening'
    return None


def _remap_wysiwyg_assets(wysiwyg_data, pk_map):
    """Deep-copy ``wysiwyg_data`` and rewrite figure/media asset references to the
    freshly-cloned assets.

    Content blocks reference assets by ``assetRef`` (``asset_<kind>_<pk:03d>``)
    and cache a display ``assetUrl``. Cloning assets to a new revision changes
    their primary keys, so both must be remapped or every figure and media block
    breaks. ``pk_map`` is ``{old_asset_pk: new_asset}`` from ``_copy_assets``.
    """
    if not wysiwyg_data:
        return wysiwyg_data

    ref_map = {}
    for old_pk, new_asset in pk_map.items():
        old_id = f'asset_{new_asset.kind}_{old_pk:03d}'
        new_id = f'asset_{new_asset.kind}_{new_asset.pk:03d}'
        ref_map[old_id] = (new_id, new_asset.file.url if new_asset.file else '')

    data = copy.deepcopy(wysiwyg_data)

    def _walk(node):
        if isinstance(node, dict):
            ref = node.get('assetRef')
            if ref in ref_map:
                new_id, new_url = ref_map[ref]
                node['assetRef'] = new_id
                node['assetUrl'] = new_url
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(data)
    return data


def _get_or_create_resubmission_draft(sub):
    """Return the in-progress WYSIWYG resubmission draft, creating it (as a clone
    of the latest revision) on first entry so it can be resumed on later visits."""
    draft = (sub.revisions
             .filter(status='draft', source_type=RevisionSource.WYSIWYG)
             .order_by('-version').first())
    if draft:
        return draft

    previous = sub.revisions.order_by('-version').first()
    next_version = (previous.version if previous else 0) + 1
    draft = SubmissionRevision.objects.create(
        submission=sub,
        version=next_version,
        source_type=RevisionSource.WYSIWYG,
        status='draft',
    )
    if previous:
        pk_map = _copy_assets(previous, draft)
        draft.wysiwyg_data = _remap_wysiwyg_assets(previous.wysiwyg_data, pk_map)
        draft.save(update_fields=['wysiwyg_data'])
    return draft


@login_required
def resubmit_wysiwyg_editor(request, pk):
    """Reopen the online editor to revise an editor-authored manuscript."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    if _resubmit_mode(sub) is None:
        messages.error(request, 'This submission is not currently open for revision.')
        return redirect('submission_detail', pk=pk)

    # Guard against .tex-authored submissions reaching this URL directly.
    latest = sub.revisions.order_by('-version').first()
    if latest and latest.source_type == RevisionSource.LATEX and not latest.wysiwyg_data:
        return redirect('resubmit_step1', pk=sub.pk)

    rev = _get_or_create_resubmission_draft(sub)

    import json as _json
    from apps.journal.models import ArticleType
    wysiwyg_json = _json.dumps(rev.wysiwyg_data) if rev.wysiwyg_data else 'null'

    return render(request, 'author/submit_step2_wysiwyg.html', {
        'submission': sub,
        'revision': rev,
        'wysiwyg_json': wysiwyg_json,
        'article_types': ArticleType.choices,
        'is_resubmission': True,
        'continue_url': reverse('resubmit_wysiwyg_confirm', args=[sub.pk, rev.pk]),
    })


@login_required
def resubmit_wysiwyg_confirm(request, pk, rev):
    """Confirm and submit an editor-authored revision (response letter + notes)."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(
        SubmissionRevision, pk=rev, submission=sub,
        status='draft', source_type=RevisionSource.WYSIWYG,
    )
    mode = _resubmit_mode(sub)
    if mode is None:
        messages.error(request, 'This submission is not currently open for revision.')
        return redirect('submission_detail', pk=pk)

    if request.method == 'POST':
        revision.notes = request.POST.get('notes', '')
        if request.FILES.get('response_letter'):
            revision.response_letter = request.FILES['response_letter']
        kw = request.POST.get('keywords', '')
        updated_kw = [k.strip() for k in kw.replace(';', ',').split(',') if k.strip()]
        if updated_kw and updated_kw != (sub.keywords or []):
            sub.keywords = updated_kw
            sub.save(update_fields=['keywords'])

        revision.status = 'submitted'
        revision.submitted_at = timezone.now()
        revision.save()

        if mode == 'review':
            sub.status = SubmissionStatus.REVISED
            sub.save(update_fields=['status'])
            from apps.notifications.tasks import notify_revision_submitted
            notify_revision_submitted(revision.pk)
            messages.success(request, 'Your revision has been submitted. The editorial team will be in touch.')
        else:  # screening correction
            sub.status = SubmissionStatus.SUBMITTED
            sub.submission_date = timezone.now()
            sub.save(update_fields=['status', 'submission_date'])
            from apps.notifications.tasks import notify_screening_resubmission
            notify_screening_resubmission(revision.pk)
            messages.success(request, 'Corrected manuscript submitted. The editorial team will be in touch.')
        return redirect('author_dashboard')

    context = {
        'submission': sub,
        'revision': revision,
        'mode': mode,
        'editor_url': reverse('resubmit_wysiwyg_editor', args=[sub.pk]),
    }
    if mode == 'review':
        context['decision'] = sub.editorial_decisions.order_by('-round').first()
    else:
        context['screening'] = (sub.screening_checks
                                .filter(result='return_to_author')
                                .order_by('-checked_at').first())
    return render(request, 'author/resubmit_wysiwyg_confirm.html', context)
