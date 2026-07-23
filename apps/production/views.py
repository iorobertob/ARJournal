import hashlib
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse, Http404
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from .models import HTMLBuild, PDFExport, DOIDeposit
from apps.documents.models import CanonicalDocument


def _dispatch_task(task, *args):
    """
    Run a Celery task synchronously in dev, async in production.

    CELERY_TASK_ALWAYS_EAGER was removed in Celery 5 — calling .delay() always
    tries to reach a real broker even in dev. Use task.apply() to run inline
    without a broker when the setting is True.
    """
    from django.conf import settings
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        task.apply(args=args)
    else:
        task.delay(*args)


def editorial_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_editorial_access():
            return render(request, '403.html', {'message': 'Editorial access required.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@editorial_required
def trigger_ingest(request, submission_pk):
    """Run the ingest task for the current revision and redirect back."""
    from django.views.decorators.http import require_POST
    if request.method != 'POST':
        return redirect('editorial_submission', pk=submission_pk)
    from apps.submissions.models import Submission
    from apps.production.tasks import ingest_submission
    sub = get_object_or_404(Submission, pk=submission_pk)
    revision = sub.get_current_revision()
    if not revision:
        messages.error(request, 'No revision found to ingest.')
        return redirect('editorial_submission', pk=submission_pk)
    try:
        ingest_submission(revision.pk)
        messages.success(request, 'Manuscript parsed and ingested successfully.')
    except Exception as e:
        messages.error(request, f'Ingest failed: {e}')
    return redirect('editorial_submission', pk=submission_pk)


@editorial_required
def build_html(request, document_pk):
    """Build and publish the HTML for a canonical document."""
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    from apps.documents.renderers.html_renderer import render_html, build_toc
    submission = doc.revision.submission
    html = render_html(doc.data, submission)
    toc = build_toc(doc.data)
    build_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
    build = HTMLBuild.objects.filter(
        document__revision__submission=submission
    ).first()
    if build:
        build.document = doc
    else:
        build = HTMLBuild(document=doc)
    build.html_content = html
    build.table_of_contents = toc
    build.build_hash = build_hash
    build.save()
    doc.html_build_ok = True
    doc.save(update_fields=['html_build_ok'])
    messages.success(request, 'HTML build complete.')
    return redirect('editorial_submission', pk=doc.revision.submission.pk)


@editorial_required
def publish_article(request, document_pk):
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    build = get_object_or_404(HTMLBuild, document=doc)
    if request.method == 'POST':
        build.is_published = True
        build.published_at = timezone.now()
        build.access_mode = request.POST.get('access_mode', 'open')
        build.save()
        from apps.submissions.models import SubmissionStatus
        submission = doc.revision.submission
        submission.status = SubmissionStatus.PUBLISHED
        submission.save()
        from apps.notifications.tasks import notify_article_published, notify_editors_article_published
        notify_article_published(submission.pk)
        notify_editors_article_published(submission.pk)
        messages.success(request, 'Article published.')
    return redirect('editorial_submission', pk=doc.revision.submission.pk)


@editorial_required
def unpublish_article(request, document_pk):
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    build = get_object_or_404(HTMLBuild, document=doc)
    if request.method == 'POST':
        build.is_published = False
        build.published_at = None
        build.save()
        from apps.submissions.models import SubmissionStatus
        submission = doc.revision.submission
        submission.status = SubmissionStatus.IN_PRODUCTION
        submission.save()
        messages.success(request, 'Article unpublished and returned to in-production.')
    return redirect('editorial_submission', pk=doc.revision.submission.pk)


@editorial_required
def update_slug(request, document_pk):
    """Allow editors to set a custom URL slug for an article."""
    if request.method != 'POST':
        return redirect('editorial_submission', pk=get_object_or_404(CanonicalDocument, pk=document_pk).revision.submission.pk)

    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    submission = doc.revision.submission

    import re
    raw = request.POST.get('slug', '').strip()
    new_slug = re.sub(r'[^a-z0-9]+', '-', raw.lower()).strip('-')

    if not new_slug:
        messages.error(request, 'Slug cannot be empty.')
        return redirect('editorial_submission', pk=submission.pk)

    from apps.submissions.models import Submission
    if Submission.objects.filter(slug=new_slug).exclude(pk=submission.pk).exists():
        messages.error(request, f'The slug "{new_slug}" is already in use by another article.')
        return redirect('editorial_submission', pk=submission.pk)

    old_slug = submission.slug
    submission.slug = new_slug
    submission.save(update_fields=['slug'])

    # Keep HTMLBuild slug in sync
    try:
        build = doc.html_build
        build.slug = new_slug
        build.save(update_fields=['slug'])
    except HTMLBuild.DoesNotExist:
        pass

    messages.success(request, f'Article URL slug updated: /articles/{new_slug}/')
    return redirect('editorial_submission', pk=submission.pk)


@editorial_required
def admin_preview(request, document_pk):
    """Admin HTML preview — works for any build, published or not.
    Falls back to rendering from canonical JSON when no HTMLBuild exists yet
    (e.g. annotations on a revision that was never put into production)."""
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    build = HTMLBuild.objects.filter(document=doc).first()
    submission = doc.revision.submission

    toc = []
    article_html = None
    if build:
        toc = build.table_of_contents or []
        article_html = build.html_content
    else:
        from apps.documents.renderers.html_renderer import render_html, build_toc
        try:
            article_html = render_html(doc.data, revision=doc.revision)
            toc = build_toc(doc.data)
        except Exception:
            pass

    return render(request, 'public/article.html', {
        'build': build,
        'submission': submission,
        'toc': toc,
        'admin_preview': True,
        'article_html': article_html,
    })


@editorial_required
def admin_request_pdf(request, document_pk):
    """Admin PDF generation — works for any built article, published or not."""
    from datetime import timedelta
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    get_object_or_404(HTMLBuild, document=doc)  # must have a build
    exp = PDFExport.objects.create(
        document=doc,
        mode='flat',  # interactive PDF retired — only flat PDFs are generated
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    from .tasks import generate_pdf
    _dispatch_task(generate_pdf, exp.pk)
    exp.refresh_from_db()
    return HttpResponseRedirect(reverse('download_pdf', args=[exp.download_token]))


def request_pdf(request, document_pk):
    """
    Request a PDF export.

    Flat mode  → generate synchronously, return FileResponse immediately.
                 No intermediate page needed.
    Interactive → dispatch (possibly async), redirect to the waiting/polling page.
    """
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    get_object_or_404(HTMLBuild, document=doc, is_published=True)
    from datetime import timedelta
    from .tasks import generate_pdf

    exp = PDFExport.objects.create(
        document=doc,
        mode='flat',  # interactive PDF retired — only flat PDFs are generated
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    # Run synchronously regardless of Celery config — the PDF is generated and
    # returned immediately for download.
    generate_pdf.apply(args=(exp.pk,))
    exp.refresh_from_db()
    if exp.file:
        fname = f'{doc.revision.submission.slug or "article"}.pdf'
        return FileResponse(
            exp.file.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=fname,
        )
    messages.error(request, 'PDF generation failed. Please try again.')
    return redirect(request.META.get('HTTP_REFERER') or reverse('home'))


def download_pdf(request, token):
    """
    Serve a completed PDF export, or show/poll its status.

    GET ?json=1  → JSON status check for the polling page: {ready, error}
    Otherwise    → serve the file (attachment) if ready, else render waiting page.
    """
    from django.http import JsonResponse
    exp = get_object_or_404(PDFExport, download_token=token)

    expired = exp.expires_at < timezone.now()

    if request.GET.get('json'):
        if expired:
            return JsonResponse({'error': 'expired'})
        return JsonResponse({'ready': bool(exp.file)})

    if expired:
        raise Http404('This PDF export has expired.')

    if not exp.file:
        return render(request, 'public/pdf_pending.html', {'export': exp})

    fname = (
        exp.document.revision.submission.slug or 'article'
    ) + '.pdf'
    response = FileResponse(
        exp.file.open('rb'),
        content_type='application/pdf',
        as_attachment=True,
        filename=fname,
    )
    exp.downloaded = True
    exp.save(update_fields=['downloaded'])
    return response


# ── Protected media streaming ─────────────────────────────────────────────────
def _media_content_type(norm):
    ext = norm.rsplit('.', 1)[-1].lower()
    return {
        'ts': 'video/mp2t', 'm4s': 'video/iso.segment',
        'm3u8': 'application/vnd.apple.mpegurl',
        'mp4': 'video/mp4', 'mov': 'video/quicktime', 'webm': 'video/webm',
        'mp3': 'audio/mpeg', 'aac': 'audio/aac', 'm4a': 'audio/mp4',
        'wav': 'audio/wav', 'ogg': 'audio/ogg', 'flac': 'audio/flac',
    }.get(ext, 'application/octet-stream')


def _stream_referer_ok(request):
    """Anti-hotlink: if a Referer/Origin is present it must be same-site.

    Native players sometimes omit it, so an absent header is allowed — the
    signed, short-lived token is the primary access gate.
    """
    from django.conf import settings
    from urllib.parse import urlparse
    ref = request.META.get('HTTP_REFERER') or request.META.get('HTTP_ORIGIN')
    if not ref:
        return True
    host = urlparse(ref).netloc.split('@')[-1].split(':')[0].lower()
    allowed = {h.lower().lstrip('.') for h in getattr(settings, 'ALLOWED_HOSTS', []) if h != '*'}
    allowed.add(request.get_host().split(':')[0].lower())
    if not allowed:
        return True
    return host in allowed or any(host.endswith('.' + a) for a in allowed)


def _rewrite_playlist(abs_path, norm):
    """Return the playlist text with each segment/sub-playlist URI replaced by a
    freshly-signed stream URL (so nothing in it is a permanent/guessable link)."""
    from apps.production.media_access import signed_stream_url
    base_dir = norm.rsplit('/', 1)[0] if '/' in norm else ''
    out = []
    with open(abs_path) as fh:
        for line in fh.read().splitlines():
            s = line.strip()
            if s and not s.startswith('#'):
                child = f'{base_dir}/{s}' if base_dir else s
                out.append(signed_stream_url(child))
            else:
                out.append(line)
    return '\n'.join(out) + '\n'


def stream_media(request, media_path):
    """Serve HLS playlists/segments (and protected originals) via signed URLs.

    Blocks expired/tampered links and cross-site hotlinking. Playlists are
    rewritten so every child URI carries its own fresh token; segments are
    handed to Nginx via X-Accel-Redirect in production, or streamed by Django
    in dev (no Nginx).
    """
    import os
    import posixpath
    from urllib.parse import quote
    from django.conf import settings
    from django.http import (HttpResponse, HttpResponseForbidden,
                             HttpResponseBadRequest, FileResponse)
    from apps.production.media_access import verify

    if not verify(media_path, request.GET.get('exp'), request.GET.get('t')):
        return HttpResponseForbidden('Invalid or expired media link.')
    if not _stream_referer_ok(request):
        return HttpResponseForbidden('Cross-site media access is not allowed.')

    norm = posixpath.normpath(media_path)
    if norm.startswith(('..', '/')) or '..' in norm.split('/'):
        return HttpResponseBadRequest('Bad media path.')

    abs_path = os.path.join(settings.MEDIA_ROOT, norm)
    if not os.path.isfile(abs_path):
        raise Http404('Media not found.')

    if norm.endswith('.m3u8'):
        resp = HttpResponse(_rewrite_playlist(abs_path, norm),
                            content_type='application/vnd.apple.mpegurl')
        resp['Cache-Control'] = 'private, max-age=30'
        return resp

    content_type = _media_content_type(norm)
    if getattr(settings, 'USE_X_ACCEL', False):
        # Nginx serves the bytes (with range support) from an internal location.
        resp = HttpResponse(status=200)
        resp['Content-Type'] = content_type
        resp['X-Accel-Redirect'] = settings.MEDIA_URL.rstrip('/') + '/' + quote(norm)
        return resp
    resp = FileResponse(open(abs_path, 'rb'), content_type=content_type)
    resp['Accept-Ranges'] = 'bytes'
    return resp
