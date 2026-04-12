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
    html = render_html(doc.data, doc.revision.submission)
    toc = build_toc(doc.data)
    build_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
    build, _ = HTMLBuild.objects.get_or_create(document=doc)
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
    """Request an ephemeral PDF export."""
    doc = get_object_or_404(CanonicalDocument, pk=document_pk)
    build = get_object_or_404(HTMLBuild, document=doc, is_published=True)
    from datetime import timedelta
    exp = PDFExport.objects.create(
        document=doc,
        mode=request.GET.get('mode', 'flat'),
        expires_at=timezone.now() + timedelta(minutes=30),
    )
    from .tasks import generate_pdf
    _dispatch_task(generate_pdf, exp.pk)
    exp.refresh_from_db()
    return render(request, 'public/pdf_pending.html', {
        'export': exp,
        'build': build,
    })


def download_pdf(request, token):
    exp = get_object_or_404(PDFExport, download_token=token)
    if exp.expires_at < timezone.now():
        raise Http404('This PDF export has expired.')
    if not exp.file:
        return render(request, 'public/pdf_pending.html', {'export': exp})
    response = FileResponse(exp.file.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="article.pdf"'
    exp.downloaded = True
    exp.save(update_fields=['downloaded'])
    return response
