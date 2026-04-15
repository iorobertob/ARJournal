import hashlib
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse, Http404
from django.contrib import messages
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
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('Editorial access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


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
        messages.success(request, 'Article published.')
    return redirect('editorial_submission', pk=doc.revision.submission.pk)


@editorial_required
def admin_preview(request, document_pk):
    """Admin HTML preview — works for any build, published or not."""
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    build = get_object_or_404(HTMLBuild, document=doc)
    submission = doc.revision.submission
    toc = build.table_of_contents or []
    return render(request, 'public/article.html', {
        'build': build,
        'submission': submission,
        'toc': toc,
        'admin_preview': True,
    })


@editorial_required
def admin_request_pdf(request, document_pk):
    """Admin PDF generation — works for any built article, published or not."""
    from datetime import timedelta
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    get_object_or_404(HTMLBuild, document=doc)  # must have a build
    mode = request.GET.get('mode', 'flat')
    exp = PDFExport.objects.create(
        document=doc,
        mode=mode,
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
    mode = request.GET.get('mode', 'flat')
    from datetime import timedelta
    from .tasks import generate_pdf

    exp = PDFExport.objects.create(
        document=doc,
        mode=mode,
        expires_at=timezone.now() + timedelta(minutes=30),
    )

    if mode == 'flat':
        # Run synchronously regardless of Celery config — flat PDFs are fast
        # and the user expects an immediate download.
        generate_pdf.apply(args=(exp.pk,))
        exp.refresh_from_db()
        if exp.file:
            fname = f'{doc.revision.submission.slug or "article"}.pdf'
            response = FileResponse(
                exp.file.open('rb'),
                content_type='application/pdf',
                as_attachment=True,
                filename=fname,
            )
            return response
        # Generation failed — show a simple error
        messages.error(request, 'PDF generation failed. Please try again.')
        return redirect(request.META.get('HTTP_REFERER', '/'))

    else:
        # Interactive PDF: always show the spinner page so the user sees
        # progress feedback. In dev (always-eager) the task runs synchronously
        # before this line, so polling will return ready immediately and
        # auto-trigger the download. In production the worker runs it async.
        _dispatch_task(generate_pdf, exp.pk)
        return render(request, 'public/pdf_pending.html', {'export': exp})


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
