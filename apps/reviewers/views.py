from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
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
    from .scorer import suggest_reviewers
    result = suggest_reviewers(submission)
    # Persist suggestions
    ReviewerSuggestion.objects.filter(submission=submission).delete()
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
            submission=submission, status=SuggestionStatus.APPROVED
        )
        deadline = request.POST.get('deadline')
        for suggestion in approved:
            inv, created = ReviewerInvitation.objects.get_or_create(
                submission=submission,
                reviewer=suggestion.reviewer,
                defaults={'deadline': deadline or (timezone.now().date() + timezone.timedelta(days=21))},
            )
            if created:
                suggestion.status = SuggestionStatus.INVITED
                suggestion.save()
                from apps.notifications.tasks import notify_reviewer_invited
                notify_reviewer_invited.delay(inv.pk)
        from apps.submissions.models import SubmissionStatus
        submission.status = SubmissionStatus.UNDER_REVIEW
        submission.save()
        messages.success(request, 'Invitations sent.')
    return redirect('editorial_submission', pk=submission_pk)


def invitation_response(request, token):
    """Magic-link handler: reviewer accepts or declines an invitation."""
    inv = get_object_or_404(ReviewerInvitation, magic_token=token)
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
