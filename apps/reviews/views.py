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
def reviewer_dashboard(request):
    """Dashboard for reviewers: active reviews, pending invitations, history."""
    base_qs = (
        ReviewerInvitation.objects
        .filter(reviewer=request.user)
        .select_related('submission', 'submission__author')
        .order_by('-sent_at')
    )

    # Build active list with associated Review object
    active_items = []
    for inv in base_qs.filter(status='accepted'):
        review = None
        try:
            review = inv.review
        except Exception:
            pass
        active_items.append({'invitation': inv, 'review': review})

    pending = list(base_qs.filter(status='pending'))
    history = list(base_qs.filter(status__in=['declined', 'expired']))

    # Also include submitted/completed reviews in history
    submitted_items = []
    for inv in base_qs.filter(status='accepted'):
        try:
            r = inv.review
            if r and r.status in (ReviewStatus.SUBMITTED, ReviewStatus.MODERATED, ReviewStatus.RELEASED):
                submitted_items.append({'invitation': inv, 'review': r})
        except Exception:
            pass

    return render(request, 'reviewer/dashboard.html', {
        'active_items': active_items,
        'pending_invitations': pending,
        'history_invitations': history,
        'submitted_items': submitted_items,
        'today': timezone.now().date(),
    })


@login_required
def reviewer_workspace(request, invitation_pk):
    invitation = get_object_or_404(ReviewerInvitation, pk=invitation_pk)
    # Allow the assigned reviewer OR any editorial user
    if invitation.reviewer != request.user and not request.user.has_editorial_access():
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('You do not have access to this review workspace.')
    review, _ = Review.objects.get_or_create(invitation=invitation)
    submission = invitation.submission
    revision = submission.get_current_revision()

    # Auto-ingest .tex manuscript if no canonical doc exists yet
    canonical_doc_obj = None
    ingest_error = None
    if revision:
        try:
            canonical_doc_obj = revision.canonical_document
        except Exception:
            pass
        if canonical_doc_obj is None and revision.manuscript_file:
            fname = revision.manuscript_file.name.lower()
            if fname.endswith('.tex'):
                try:
                    from apps.production.tasks import ingest_submission
                    ingest_submission(revision.pk)  # run synchronously
                    revision.refresh_from_db()
                    try:
                        canonical_doc_obj = revision.canonical_document
                    except Exception:
                        pass
                except Exception as e:
                    ingest_error = str(e)

    canonical_doc = canonical_doc_obj.data if canonical_doc_obj else {}

    from apps.documents.renderers.html_renderer import render_html, build_toc
    if canonical_doc:
        article_html = render_html(canonical_doc, submission)
        toc = build_toc(canonical_doc)
    else:
        article_html = None  # template will show fallback
        toc = []

    annotations = review.annotations.filter(resolved=False)
    return render(request, 'reviewer/workspace.html', {
        'invitation': invitation,
        'review': review,
        'submission': submission,
        'revision': revision,
        'article_html': article_html,
        'toc': toc,
        'annotations': annotations,
        'ingest_error': ingest_error,
    })


@login_required
@require_POST
def save_draft(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk)
    if review.invitation.reviewer != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
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
    review = get_object_or_404(Review, pk=review_pk)
    if review.invitation.reviewer != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
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
    notify_review_submitted(review.pk)
    return JsonResponse({'status': 'submitted'})


@login_required
@require_POST
def add_annotation(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk)
    if review.invitation.reviewer != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
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



