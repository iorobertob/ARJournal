import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Review, ReviewAnnotation, ReviewModeration, ReviewStatus, ModerationStatus
from apps.reviewers.models import ReviewerInvitation


@login_required
def reviewer_workspace(request, invitation_pk):
    invitation = get_object_or_404(ReviewerInvitation, pk=invitation_pk, reviewer=request.user)
    review, _ = Review.objects.get_or_create(invitation=invitation)
    submission = invitation.submission
    revision = submission.get_current_revision()
    canonical_doc = getattr(getattr(revision, 'canonical_document', None), 'data', {}) if revision else {}

    # Build HTML content
    from apps.documents.renderers.html_renderer import render_html, build_toc
    if canonical_doc:
        article_html = render_html(canonical_doc, submission)
        toc = build_toc(canonical_doc)
    else:
        article_html = '<p>Manuscript content not yet available.</p>'
        toc = []

    annotations = review.annotations.filter(resolved=False)
    return render(request, 'reviewer/workspace.html', {
        'invitation': invitation,
        'review': review,
        'submission': submission,
        'article_html': article_html,
        'toc': toc,
        'annotations': annotations,
    })


@login_required
@require_POST
def save_draft(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk, invitation__reviewer=request.user)
    data = json.loads(request.body)
    review.summary = data.get('summary', review.summary)
    review.strengths = data.get('strengths', review.strengths)
    review.major_issues = data.get('major_issues', review.major_issues)
    review.minor_issues = data.get('minor_issues', review.minor_issues)
    review.ethical_concerns = data.get('ethical_concerns', review.ethical_concerns)
    review.comments_to_author = data.get('comments_to_author', review.comments_to_author)
    review.comments_to_editor = data.get('comments_to_editor', review.comments_to_editor)
    review.recommendation = data.get('recommendation', review.recommendation)
    review.draft_saved_at = timezone.now()
    review.save()
    return JsonResponse({'saved_at': review.draft_saved_at.isoformat()})


@login_required
@require_POST
def submit_review(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk, invitation__reviewer=request.user)
    if not review.summary or not review.recommendation:
        return JsonResponse({'error': 'Summary and recommendation are required.'}, status=400)
    review.status = ReviewStatus.SUBMITTED
    review.submitted_at = timezone.now()
    review.save()
    # Create moderation record
    ReviewModeration.objects.get_or_create(
        review=review,
        defaults={
            'original_comments_to_author': review.comments_to_author,
            'moderated_comments_to_author': review.comments_to_author,
        }
    )
    from apps.notifications.tasks import notify_review_submitted
    notify_review_submitted.delay(review.pk)
    return JsonResponse({'status': 'submitted'})


@login_required
@require_POST
def add_annotation(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk, invitation__reviewer=request.user)
    data = json.loads(request.body)
    ann = ReviewAnnotation.objects.create(
        review=review,
        block_id=data.get('block_id', ''),
        anchor_id=data.get('anchor_id', ''),
        comment=data.get('comment', ''),
        selector_data=data.get('selector_data', {}),
    )
    return JsonResponse({'id': ann.pk, 'block_id': ann.block_id, 'comment': ann.comment})


# ── Editorial moderation view ─────────────────────────────────────────────────

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
def moderate_review(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk)
    moderation, _ = ReviewModeration.objects.get_or_create(
        review=review,
        defaults={
            'original_comments_to_author': review.comments_to_author,
            'moderated_comments_to_author': review.comments_to_author,
        }
    )
    if request.method == 'POST':
        moderation.moderated_comments_to_author = request.POST.get(
            'moderated_comments', moderation.moderated_comments_to_author
        )
        moderation.moderation_notes = request.POST.get('notes', moderation.moderation_notes)
        moderation.conflict_flagged = bool(request.POST.get('conflict_flagged'))
        moderation.conflict_note = request.POST.get('conflict_note', '')
        moderation.status = ModerationStatus.MODERATED
        moderation.editor = request.user
        moderation.moderated_at = timezone.now()
        moderation.save()
        review.status = ReviewStatus.MODERATED
        review.save()
        messages.success(request, 'Review moderated.')
        return redirect('editorial_submission', pk=review.submission.pk)
    return render(request, 'editorial/moderate_review.html', {
        'review': review, 'moderation': moderation
    })
