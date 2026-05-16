import json
import re
import bibtexparser
from bibtexparser.bparser import BibTexParser

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from .models import Submission, SubmissionRevision, SubmissionStatus, RevisionSource
from .views import _upsert_asset


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
