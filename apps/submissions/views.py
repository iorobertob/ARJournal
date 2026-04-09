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
            kind = _guess_kind(f.content_type)
            SubmissionAsset.objects.create(
                revision=revision,
                kind=kind,
                file=f,
                original_filename=f.name,
                mime_type=f.content_type,
            )
        if request.POST.get('done'):
            return redirect('submission_step4', pk=sub.pk, rev=revision.pk)
    assets = revision.assets.all()
    return render(request, 'author/submit_step3.html', {
        'submission': sub, 'revision': revision, 'assets': assets
    })


def _guess_kind(mime):
    if mime.startswith('image/'):
        return 'image'
    if mime.startswith('video/'):
        return 'video'
    if mime.startswith('audio/'):
        return 'audio'
    return 'supplementary'


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
        notify_submission_received.delay(sub.pk)
        messages.success(request, 'Submission received! You will receive a confirmation email.')
        return redirect('author_dashboard')
    return render(request, 'author/submit_step4.html', {
        'submission': sub, 'revision': revision
    })


@login_required
def submission_detail(request, pk):
    sub = get_object_or_404(Submission, pk=pk, author=request.user)
    revisions = sub.revisions.all()
    return render(request, 'author/submission_detail.html', {
        'submission': sub, 'revisions': revisions
    })
