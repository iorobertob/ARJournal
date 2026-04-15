from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Submission, SubmissionRevision, SubmissionAsset, SubmissionStatus


@login_required
def dashboard(request):
    submissions = Submission.objects.filter(author=request.user).order_by('-created_at')
    return render(request, 'author/dashboard.html', {'submissions': submissions})


@login_required
def new_submission_step1(request):
    """Step 1: Article type and basic metadata."""
    if request.method == 'POST':
        sub = Submission.objects.create(
            author=request.user,
            title=request.POST['title'],
            subtitle=request.POST.get('subtitle', ''),
            article_type=request.POST['article_type'],
            abstract=request.POST.get('abstract', ''),
            cover_letter=request.POST.get('cover_letter', ''),
        )
        kw = request.POST.get('keywords', '')
        sub.keywords = [k.strip() for k in kw.split(';') if k.strip()]
        sub.save()
        return redirect('submission_step2', pk=sub.pk)
    from apps.journal.models import ArticleType
    return render(request, 'author/submit_step1.html', {'article_types': ArticleType.choices})


@login_required
def new_submission_step2(request, pk):
    """Step 2: Upload manuscript file."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    if request.method == 'POST' and request.FILES.get('manuscript'):
        rev = SubmissionRevision.objects.create(
            submission=sub,
            version=1,
            manuscript_file=request.FILES['manuscript'],
        )
        return redirect('submission_step3', pk=sub.pk, rev=rev.pk)
    return render(request, 'author/submit_step2.html', {'submission': sub})


@login_required
def new_submission_step3(request, pk, rev):
    """Step 3: Upload media assets."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub)
    if request.method == 'POST':
        for f in request.FILES.getlist('assets'):
            _upsert_asset(revision, f)
        if request.POST.get('done'):
            return redirect('submission_step4', pk=sub.pk, rev=revision.pk)
    assets = revision.assets.all()
    return render(request, 'author/submit_step3.html', {
        'submission': sub, 'revision': revision, 'assets': assets
    })


def _guess_kind(mime, filename=''):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in ('bib', 'tex', 'pdf', 'doc', 'docx', 'txt', 'csv', 'zip'):
        return 'supplementary'
    if mime.startswith('image/'):
        return 'image'
    if mime.startswith('video/'):
        return 'video'
    if mime.startswith('audio/'):
        return 'audio'
    return 'supplementary'


def _upsert_asset(revision, f):
    """
    Create or replace a SubmissionAsset for an uploaded file.

    Size is read from the storage backend after the file is saved — this is
    more reliable than f.size, which some browsers/OS report as 0.
    """
    kind = _guess_kind(f.content_type, f.name)
    existing = revision.assets.filter(original_filename=f.name).first()
    if existing:
        existing.file = f
        existing.kind = kind
        existing.mime_type = f.content_type
        existing.save()
        asset = existing
    else:
        asset = SubmissionAsset.objects.create(
            revision=revision,
            kind=kind,
            file=f,
            original_filename=f.name,
            mime_type=f.content_type,
        )
    # Read size from storage after the file is fully written to disk.
    try:
        asset.size_bytes = asset.file.size
        asset.save(update_fields=['size_bytes'])
    except Exception:
        pass


@login_required
def new_submission_step4(request, pk, rev):
    """Step 4: Declarations and submit."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub)
    if request.method == 'POST':
        sub.funding_statement = request.POST.get('funding', sub.funding_statement)
        sub.conflict_of_interest = request.POST.get('conflict_of_interest', sub.conflict_of_interest)
        sub.ai_use_statement = request.POST.get('ai_use_statement', sub.ai_use_statement)
        sub.originality_confirmed = bool(request.POST.get('originality_confirmed'))
        sub.status = SubmissionStatus.SUBMITTED
        sub.submission_date = timezone.now()
        sub.save()
        revision.status = 'submitted'
        revision.submitted_at = timezone.now()
        revision.save()
        from apps.notifications.tasks import notify_submission_received
        notify_submission_received(sub.pk)
        messages.success(request, 'Submission received! You will receive a confirmation email.')
        return redirect('author_dashboard')
    return render(request, 'author/submit_step4.html', {
        'submission': sub, 'revision': revision
    })


@login_required
def submission_detail(request, pk):
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revisions = sub.revisions.all()
    decisions = sub.editorial_decisions.order_by('round')
    return render(request, 'author/submission_detail.html', {
        'submission': sub,
        'revisions': revisions,
        'decisions': decisions,
        'can_resubmit': sub.status == SubmissionStatus.REVISION_REQUESTED,
    })


# ── Resubmission wizard ───────────────────────────────────────────────────────

_RESUBMITTABLE = {SubmissionStatus.REVISION_REQUESTED}


@login_required
def resubmit_step1(request, pk):
    """Resubmission step 1: upload revised manuscript + optional response letter."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    if sub.status not in _RESUBMITTABLE:
        messages.error(request, 'This submission is not currently open for revision.')
        return redirect('submission_detail', pk=pk)

    last_decision = sub.editorial_decisions.order_by('-round').first()

    if request.method == 'POST':
        if not request.FILES.get('manuscript'):
            messages.error(request, 'Please upload your revised manuscript (.tex).')
            return render(request, 'author/resubmit_step1.html', {
                'submission': sub, 'decision': last_decision,
            })
        current_version = sub.revisions.order_by('-version').first()
        next_version = (current_version.version if current_version else 0) + 1
        rev = SubmissionRevision.objects.create(
            submission=sub,
            version=next_version,
            manuscript_file=request.FILES['manuscript'],
            notes=request.POST.get('notes', ''),
            status='draft',
        )
        if request.FILES.get('response_letter'):
            rev.response_letter = request.FILES['response_letter']
            rev.save()
        # Copy assets from the previous revision so authors only re-upload what changed.
        if current_version:
            for old_asset in current_version.assets.all():
                new_asset = SubmissionAsset.objects.create(
                    revision=rev,
                    kind=old_asset.kind,
                    file=old_asset.file.name,
                    original_filename=old_asset.original_filename,
                    mime_type=old_asset.mime_type,
                    caption=old_asset.caption,
                    alt_text=old_asset.alt_text,
                    rights_cleared=old_asset.rights_cleared,
                )
                # Resolve size from storage (old records may have size_bytes=0).
                try:
                    new_asset.size_bytes = new_asset.file.size
                    new_asset.save(update_fields=['size_bytes'])
                except Exception:
                    pass
        return redirect('resubmit_step2', pk=sub.pk, rev=rev.pk)

    return render(request, 'author/resubmit_step1.html', {
        'submission': sub,
        'decision': last_decision,
    })


@login_required
def resubmit_step2(request, pk, rev):
    """Resubmission step 2: upload media assets."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub)
    if sub.status not in _RESUBMITTABLE:
        messages.error(request, 'This submission is not currently open for revision.')
        return redirect('submission_detail', pk=pk)

    if request.method == 'POST':
        for f in request.FILES.getlist('assets'):
            _upsert_asset(revision, f)
        if request.POST.get('done'):
            return redirect('resubmit_step3', pk=sub.pk, rev=revision.pk)

    assets = revision.assets.all()
    return render(request, 'author/resubmit_step2.html', {
        'submission': sub,
        'revision': revision,
        'assets': assets,
    })


@login_required
def resubmit_step3(request, pk, rev):
    """Resubmission step 3: confirm and submit the revision."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub)
    if sub.status not in _RESUBMITTABLE:
        messages.error(request, 'This submission is not currently open for revision.')
        return redirect('submission_detail', pk=pk)

    if request.method == 'POST':
        sub.status = SubmissionStatus.REVISED
        sub.save()
        revision.status = 'submitted'
        revision.submitted_at = timezone.now()
        revision.save()
        from apps.notifications.tasks import notify_revision_submitted
        notify_revision_submitted(revision.pk)
        messages.success(request, 'Your revision has been submitted. The editorial team will be in touch.')
        return redirect('author_dashboard')

    return render(request, 'author/resubmit_step3.html', {
        'submission': sub,
        'revision': revision,
        'assets': revision.assets.all(),
    })


@login_required
def delete_revision_asset(request, pk, rev, asset_pk):
    """Remove a single asset from a draft revision (POST only)."""
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revision = get_object_or_404(SubmissionRevision, pk=rev, submission=sub, status='draft')
    asset = get_object_or_404(SubmissionAsset, pk=asset_pk, revision=revision)
    asset.delete()
    # Return to whichever step the user came from
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if next_url:
        return redirect(next_url)
    # Fallback: initial step3 or resubmit step2 depending on revision version
    if revision.version == 1:
        return redirect('submission_step3', pk=sub.pk, rev=rev)
    return redirect('resubmit_step2', pk=sub.pk, rev=rev)
