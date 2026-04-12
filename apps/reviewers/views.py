from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import ReviewerProfile, ReviewerSuggestion, ReviewerInvitation, SuggestionStatus
from apps.submissions.models import Submission


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
def generate_suggestions(request, submission_pk):
    submission = get_object_or_404(Submission, pk=submission_pk)

    # Remember manually-removed reviewers so they don't come back
    excluded_pks = set(
        ReviewerSuggestion.objects.filter(
            submission=submission,
            status=SuggestionStatus.REJECTED,
        ).values_list('reviewer_id', flat=True)
    )

    from .scorer import suggest_reviewers
    result = suggest_reviewers(submission, excluded_pks=excluded_pks)
    # Persist suggestions (keep REJECTED entries; only replace non-rejected)
    ReviewerSuggestion.objects.filter(submission=submission).exclude(
        status=SuggestionStatus.REJECTED
    ).delete()
    for item in result['primary']:
        ReviewerSuggestion.objects.create(
            submission=submission,
            reviewer=item['reviewer'],
            score=item['score'],
            breakdown=item['breakdown'],
            rationale=item['rationale'],
            is_primary=True,
        )
    for item in result['alternates']:
        ReviewerSuggestion.objects.create(
            submission=submission,
            reviewer=item['reviewer'],
            score=item['score'],
            breakdown=item['breakdown'],
            rationale=item['rationale'],
            is_primary=False,
        )

    # XHR: return rendered suggestion cards partial
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        suggestions = ReviewerSuggestion.objects.filter(submission=submission)
        invitations = ReviewerInvitation.objects.filter(submission=submission)
        from django.template.loader import render_to_string
        html = render_to_string('editorial/_suggestion_cards.html', {
            'suggestions': suggestions,
            'invitations': invitations,
            'submission': submission,
        }, request=request)
        return JsonResponse({'html': html})

    messages.success(request, 'Reviewer suggestions generated.')
    return redirect('editorial_submission', pk=submission_pk)


@editorial_required
def approve_reviewer(request, suggestion_pk):
    suggestion = get_object_or_404(ReviewerSuggestion, pk=suggestion_pk)
    suggestion.status = SuggestionStatus.APPROVED
    suggestion.suggested_by_editor = request.user
    suggestion.save()
    messages.success(request, f'{suggestion.reviewer.display_name} approved.')
    return redirect('editorial_submission', pk=suggestion.submission.pk)


@editorial_required
def send_invitations(request, submission_pk):
    """Send invitations to all approved suggestions."""
    submission = get_object_or_404(Submission, pk=submission_pk)
    if request.method == 'POST':
        approved = ReviewerSuggestion.objects.filter(
            submission=submission,
            status__in=[SuggestionStatus.APPROVED, SuggestionStatus.INVITED],
        )
        deadline = request.POST.get('deadline')
        deadline_date = deadline or (timezone.now().date() + timezone.timedelta(days=21))
        sent_count = 0
        for suggestion in approved:
            inv, created = ReviewerInvitation.objects.get_or_create(
                submission=submission,
                reviewer=suggestion.reviewer,
                defaults={'deadline': deadline_date},
            )
            if not created and deadline:
                # Update deadline on resend
                inv.deadline = deadline_date
                inv.save(update_fields=['deadline'])
            if created:
                suggestion.status = SuggestionStatus.INVITED
                suggestion.save()
            # Always send/resend the notification email
            from apps.notifications.tasks import notify_reviewer_invited
            notify_reviewer_invited(inv.pk)
            # Update profile stats (last_invited_at, active_invitations_count)
            from apps.reviewers.profile_stats import recompute_reviewer_profile
            recompute_reviewer_profile(suggestion.reviewer)
            sent_count += 1
        from apps.submissions.models import SubmissionStatus
        submission.status = SubmissionStatus.UNDER_REVIEW
        submission.save()
        messages.success(request, f'Invitations sent to {sent_count} reviewer{"s" if sent_count != 1 else ""}.')
    return redirect('editorial_submission', pk=submission_pk)


@editorial_required
def reviewer_search_json(request, submission_pk):
    """Autocomplete JSON endpoint: returns reviewers matching ?q= query."""
    from apps.accounts.models import User, UserRole
    submission = get_object_or_404(Submission, pk=submission_pk)
    q = request.GET.get('q', '').strip()

    # Exclude already-suggested reviewers and the submission author
    excluded_ids = list(
        ReviewerSuggestion.objects
        .filter(submission=submission)
        .exclude(status=SuggestionStatus.REJECTED)
        .values_list('reviewer_id', flat=True)
    )
    excluded_ids.append(submission.author_id)

    qs = User.objects.filter(roles__contains=UserRole.REVIEWER, is_active=True).exclude(pk__in=excluded_ids)
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(reviewer_profile__expertise_keywords__icontains=q)
        ).distinct()

    results = []
    for user in qs.select_related('reviewer_profile')[:50]:
        profile = getattr(user, 'reviewer_profile', None)
        keywords = profile.expertise_keywords if profile else []
        expertise = ', '.join(keywords[:4]) if keywords else (
            profile.expertise_statement[:80] if profile and profile.expertise_statement else ''
        )
        results.append({
            'id': user.pk,
            'name': user.display_name,
            'email': user.email,
            'expertise': expertise,
        })
    return JsonResponse({'results': results})


@editorial_required
@require_POST
def remove_suggestion(request, suggestion_pk):
    """Remove a reviewer suggestion. At least 1 active suggestion must remain."""
    suggestion = get_object_or_404(ReviewerSuggestion, pk=suggestion_pk)
    submission = suggestion.submission
    active_count = ReviewerSuggestion.objects.filter(
        submission=submission
    ).exclude(status=SuggestionStatus.REJECTED).count()
    if active_count <= 1:
        messages.error(request, 'At least one reviewer must remain.')
        return redirect('editorial_submission', pk=submission.pk)

    from apps.notifications.models import AuditEvent
    AuditEvent.objects.create(
        submission=submission,
        actor=request.user,
        event_type='reviewer_removed',
        payload={'note': f'Removed reviewer suggestion: {suggestion.reviewer.display_name} (score {suggestion.score:.2f})'},
    )
    suggestion.status = SuggestionStatus.REJECTED
    suggestion.save()
    messages.success(request, f'{suggestion.reviewer.display_name} removed from suggestions.')
    return redirect('editorial_submission', pk=submission.pk)


@editorial_required
@require_POST
def add_suggestion(request, submission_pk):
    """Manually add a reviewer (or replace an existing one)."""
    submission = get_object_or_404(Submission, pk=submission_pk)
    reviewer_id = request.POST.get('reviewer_id')
    replace_pk = request.POST.get('replace_suggestion_pk')  # optional

    from apps.accounts.models import User
    reviewer = get_object_or_404(User, pk=reviewer_id)

    # Guard: max 5 active suggestions (3 primary + 2 added)
    active_count = ReviewerSuggestion.objects.filter(
        submission=submission
    ).exclude(status=SuggestionStatus.REJECTED).count()

    if replace_pk:
        # Replace: reject the old one, add new
        old = get_object_or_404(ReviewerSuggestion, pk=replace_pk, submission=submission)
        from apps.notifications.models import AuditEvent
        AuditEvent.objects.create(
            submission=submission,
            actor=request.user,
            event_type='reviewer_replaced',
            payload={'note': f'Replaced {old.reviewer.display_name} with {reviewer.display_name}'},
        )
        old.status = SuggestionStatus.REJECTED
        old.save()
        active_count -= 1  # slot freed

    if active_count >= 5:
        messages.error(request, 'Maximum 5 reviewers allowed per submission.')
        return redirect('editorial_submission', pk=submission.pk)

    # Don't add duplicates
    if ReviewerSuggestion.objects.filter(
        submission=submission, reviewer=reviewer
    ).exclude(status=SuggestionStatus.REJECTED).exists():
        messages.error(request, f'{reviewer.display_name} is already in the suggestion list.')
        return redirect('editorial_submission', pk=submission.pk)

    ReviewerSuggestion.objects.create(
        submission=submission,
        reviewer=reviewer,
        score=0.0,
        breakdown={},
        rationale='Manually added by editor.',
        is_primary=False,
        status=SuggestionStatus.SUGGESTED,
        suggested_by_editor=request.user,
    )
    from apps.notifications.models import AuditEvent
    AuditEvent.objects.create(
        submission=submission,
        actor=request.user,
        event_type='reviewer_added',
        payload={'note': f'Manually added reviewer: {reviewer.display_name}'},
    )
    action = 'added as replacement' if replace_pk else 'added to suggestions'
    messages.success(request, f'{reviewer.display_name} {action}.')
    return redirect('editorial_submission', pk=submission.pk)


def invitation_response(request, token):
    """Magic-link handler: reviewer accepts or declines an invitation."""
    from django.contrib.auth import login as auth_login
    inv = get_object_or_404(ReviewerInvitation, magic_token=token)

    # If not logged in, log in as the reviewer automatically via the magic link
    if not request.user.is_authenticated:
        reviewer = inv.reviewer
        reviewer.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, reviewer)
        messages.info(request, f'Signed in as {reviewer.display_name}.')
    # If logged in as a different user, warn but still show the page
    elif request.user != inv.reviewer:
        messages.warning(
            request,
            f'Note: you are logged in as {request.user.email}, but this invitation '
            f'was sent to {inv.reviewer.email}. You are viewing it as an administrator.'
        )

    if request.method == 'POST':
        response = request.POST.get('response')
        if response == 'accept':
            inv.status = 'accepted'
            inv.save()
            messages.success(request, 'You have accepted the review invitation.')
            return redirect('reviewer_workspace', invitation_pk=inv.pk)
        elif response == 'decline':
            inv.status = 'declined'
            inv.decline_reason = request.POST.get('decline_reason', '')
            inv.save()
            messages.info(request, 'You have declined the invitation. Thank you for letting us know.')
            return redirect('home')
    return render(request, 'reviewer/invitation_response.html', {'invitation': inv})
