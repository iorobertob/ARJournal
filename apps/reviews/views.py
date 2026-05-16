import json
from django.contrib.auth.decorators import login_required
from django.db.models import Min
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import Review, ReviewAnnotation, ReviewModeration, ReviewStatus, ModerationStatus
from apps.reviewers.models import ReviewerInvitation


def _resolve_review_revision(review):
    """Return the SubmissionRevision this review was written against.

    Priority: stored FK → earliest annotation timestamp → review submitted_at
    → earliest revision (v1 safety net). Never falls back to the submission's
    current revision, which would show the wrong manuscript after resubmission.
    """
    if review.revision_id is not None:
        return review.revision

    submission = review.invitation.submission
    revisions = submission.revisions.order_by('version')  # ascending so .first() = v1

    earliest = review.annotations.aggregate(earliest=Min('created_at'))['earliest']
    if earliest is not None:
        candidate = revisions.filter(created_at__lte=earliest).order_by('-version').first()
        if candidate is None:
            candidate = revisions.filter(submitted_at__lte=earliest).order_by('-version').first()
        if candidate is not None:
            return candidate

    if review.submitted_at is not None:
        candidate = revisions.filter(created_at__lte=review.submitted_at).order_by('-version').first()
        if candidate is None:
            candidate = revisions.filter(submitted_at__lte=review.submitted_at).order_by('-version').first()
        if candidate is not None:
            return candidate

    return revisions.first()


@login_required
def reviewer_dashboard(request):
    """Dashboard for reviewers: active reviews, pending invitations, history."""
    from collections import defaultdict

    base_qs = (
        ReviewerInvitation.objects
        .filter(reviewer=request.user)
        .select_related('submission', 'submission__author')
        .order_by('-sent_at')
    )

    # ── Round-number annotation ───────────────────────────────────────────
    # Group all invitations for this reviewer by submission, sorted by sent_at,
    # and assign a 1-indexed round_number to each.
    all_invs = list(base_qs)
    inv_by_sub = defaultdict(list)
    for inv in sorted(all_invs, key=lambda x: x.sent_at):
        inv_by_sub[inv.submission_id].append(inv)

    multi_round_sub_ids = {sub_id for sub_id, invs in inv_by_sub.items() if len(invs) > 1}
    round_numbers = {}
    for sub_id, invs in inv_by_sub.items():
        for i, inv in enumerate(invs, start=1):
            round_numbers[inv.pk] = i

    for inv in all_invs:
        inv.round_number = round_numbers.get(inv.pk, 1)
        inv.is_multi_round = inv.submission_id in multi_round_sub_ids

    # Re-use annotated objects via a lookup so filtered sub-querysets stay consistent
    inv_lookup = {inv.pk: inv for inv in all_invs}

    # ── Build sections ────────────────────────────────────────────────────
    _completed = (ReviewStatus.SUBMITTED, ReviewStatus.MODERATED, ReviewStatus.RELEASED)

    active_items = []
    for inv in base_qs.filter(status='accepted'):
        inv = inv_lookup.get(inv.pk, inv)
        review = None
        try:
            review = inv.review
        except Exception:
            pass
        # Only include reviews that still need action (exclude completed rounds)
        if not review or review.status not in _completed:
            active_items.append({'invitation': inv, 'review': review})

    pending = [inv_lookup.get(inv.pk, inv) for inv in base_qs.filter(status='pending')]
    history = [inv_lookup.get(inv.pk, inv) for inv in base_qs.filter(status__in=['declined', 'expired'])]

    submitted_items = []
    for inv in base_qs.filter(status='accepted'):
        inv = inv_lookup.get(inv.pk, inv)
        try:
            r = inv.review
            if r and r.status in _completed:
                submitted_items.append({'invitation': inv, 'review': r})
        except Exception:
            pass

    # Submission IDs that have a currently non-completed active review —
    # used to show "New round in progress" on completed-review rows.
    active_submission_ids = {
        item['invitation'].submission_id
        for item in active_items
        if not item['review'] or item['review'].status not in (
            ReviewStatus.SUBMITTED, ReviewStatus.MODERATED, ReviewStatus.RELEASED
        )
    }

    return render(request, 'reviewer/dashboard.html', {
        'active_items': active_items,
        'pending_invitations': pending,
        'history_invitations': history,
        'submitted_items': submitted_items,
        'active_submission_ids': active_submission_ids,
        'today': timezone.now().date(),
    })


@login_required
def reviewer_workspace(request, invitation_pk):
    invitation = get_object_or_404(ReviewerInvitation, pk=invitation_pk)
    # Allow the assigned reviewer OR any editorial user
    if invitation.reviewer != request.user and not request.user.has_editorial_access():
        return render(request, '403.html', {'message': 'You do not have access to this review workspace.'}, status=403)
    review, _ = Review.objects.get_or_create(invitation=invitation)
    submission = invitation.submission
    current_revision = submission.get_current_revision()
    # Only auto-assign revision on a brand-new, untouched review. Once the
    # reviewer has added annotations or submitted, revision must not be
    # overwritten — after author resubmission, current_revision is v2.
    if (
        current_revision
        and review.revision_id is None
        and review.status == ReviewStatus.DRAFT
        and not review.annotations.exists()
    ):
        review.revision = current_revision
        review.save(update_fields=['revision'])
    revision = _resolve_review_revision(review)

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
        article_html = render_html(canonical_doc, revision=revision, reviewer_mode=False)
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
    # Belt-and-suspenders: lock review.revision at first-annotation time so
    # that if the author later resubmits, the FK is already set correctly.
    if review.revision_id is None:
        current = review.invitation.submission.get_current_revision()
        if current is not None:
            review.revision = current
            review.save(update_fields=['revision'])
    return JsonResponse({'id': ann.pk, 'block_id': ann.block_id, 'comment': ann.comment})


# ── Editorial moderation view ─────────────────────────────────────────────────

def editorial_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_editorial_access():
            return render(request, '403.html', {'message': 'Editorial access required.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@editorial_required
def moderate_review(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk)
    annotations = review.annotations.all().order_by('created_at')
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
        moderation.editor = request.user
        moderation.moderated_at = timezone.now()

        # Annotation release selection
        released_pks = {
            int(pk) for pk in request.POST.getlist('released_annotations')
            if str(pk).isdigit()
        }
        annotations.update(released_to_author=False)
        if released_pks:
            annotations.filter(pk__in=released_pks).update(released_to_author=True)

        action = request.POST.get('action', 'save')
        if action == 'release':
            moderation.status = ModerationStatus.RELEASED
            moderation.released_at = timezone.now()
            review.status = ReviewStatus.RELEASED
            review.save()
            from apps.notifications.tasks import notify_review_released
            notify_review_released(review.pk)
            messages.success(request, 'Review released to author.')
        else:
            moderation.status = ModerationStatus.MODERATED
            review.status = ReviewStatus.MODERATED
            review.save()
            messages.success(request, 'Moderation saved.')

        moderation.save()
        return redirect('editorial_submission', pk=review.submission.pk)

    canonical_doc = None
    try:
        rev = review.revision or review.invitation.submission.get_current_revision()
        if rev:
            canonical_doc = rev.canonical_document
    except Exception:
        pass

    return render(request, 'editorial/moderate_review.html', {
        'review': review,
        'moderation': moderation,
        'annotations': annotations,
        'canonical_doc': canonical_doc,
    })


@login_required
def review_detail(request, review_pk):
    """Read-only view of a submitted review — for reviewer, editor, or author."""
    review = get_object_or_404(Review, pk=review_pk)
    submission = review.submission

    is_reviewer = review.invitation.reviewer == request.user
    is_editor = request.user.has_editorial_access()
    is_author = submission.author == request.user

    if not (is_reviewer or is_editor or is_author):
        return render(request, '403.html', {'message': 'Access denied.'}, status=403)

    if review.status == ReviewStatus.DRAFT:
        return render(request, '403.html', {'message': 'This review has not been submitted yet.'}, status=403)

    if is_author and review.status != ReviewStatus.RELEASED:
        return render(request, '403.html', {'message': 'This review has not been released to you yet.'}, status=403)

    if is_author:
        annotations = review.annotations.filter(released_to_author=True).order_by('created_at')
    else:
        annotations = review.annotations.all().order_by('created_at')

    moderation = None
    try:
        moderation = review.moderation
    except Exception:
        pass

    canonical_doc = None
    try:
        revision = _resolve_review_revision(review)
        if revision:
            canonical_doc = revision.canonical_document
    except Exception:
        pass

    html_build = None
    try:
        if canonical_doc:
            from apps.production.models import HTMLBuild
            html_build = HTMLBuild.objects.filter(document=canonical_doc, is_published=True).first()
    except Exception:
        pass

    return render(request, 'reviews/review_detail.html', {
        'review': review,
        'submission': submission,
        'annotations': annotations,
        'moderation': moderation,
        'is_reviewer': is_reviewer,
        'is_editor': is_editor,
        'is_author': is_author,
        'canonical_doc': canonical_doc,
        'html_build': html_build,
    })


@login_required
def editor_review_preview(request, review_pk):
    """
    Read-only workspace for editors: shows the manuscript the review was written
    against with ALL annotations (released and unreleased) highlighted.
    """
    review = get_object_or_404(Review, pk=review_pk)

    if not request.user.has_editorial_access():
        return render(request, '403.html', {'message': 'Access denied.'}, status=403)

    if review.status == ReviewStatus.DRAFT:
        return render(request, '403.html', {'message': 'This review has not been submitted yet.'}, status=403)

    annotations = review.annotations.all().order_by('created_at')
    annotated_block_ids = list(annotations.values_list('block_id', flat=True))

    revision = _resolve_review_revision(review)
    article_html = None
    toc = []
    if revision:
        try:
            doc = revision.canonical_document
            from apps.documents.renderers.html_renderer import render_html, build_toc
            article_html = render_html(doc.data, revision=revision)
            toc = build_toc(doc.data)
        except Exception:
            pass

    return render(request, 'reviews/editor_review_preview.html', {
        'review': review,
        'submission': review.invitation.submission,
        'annotations': annotations,
        'annotated_block_ids': json.dumps(annotated_block_ids),
        'article_html': article_html,
        'toc': toc,
    })


@login_required
def author_preprint(request, review_pk):
    """
    Read-only preprint view for the author.
    Shows the rendered manuscript with released annotations highlighted.
    Accessible only to the submission author once the review is released.
    """
    review = get_object_or_404(Review, pk=review_pk)
    submission = review.invitation.submission

    if submission.author != request.user:
        return render(request, '403.html', {'message': 'Access denied.'}, status=403)

    if review.status != ReviewStatus.RELEASED:
        return render(request, '403.html', {'message': 'This review has not been released yet.'}, status=403)

    annotations = review.annotations.filter(released_to_author=True).order_by('created_at')
    annotated_block_ids = list(annotations.values_list('block_id', flat=True))

    revision = _resolve_review_revision(review)
    article_html = None
    toc = []
    if revision:
        try:
            doc = revision.canonical_document
            from apps.documents.renderers.html_renderer import render_html, build_toc
            article_html = render_html(doc.data, revision=revision)
            toc = build_toc(doc.data)
        except Exception:
            pass

    return render(request, 'reviews/author_preprint.html', {
        'review': review,
        'submission': submission,
        'annotations': annotations,
        'annotated_block_ids': json.dumps(annotated_block_ids),
        'article_html': article_html,
        'toc': toc,
    })



