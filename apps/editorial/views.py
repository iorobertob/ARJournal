from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from apps.submissions.models import Submission, SubmissionStatus
from .models import EditorialAssignment, ScreeningCheck, EditorialDecision, DecisionType


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
def editorial_dashboard(request):
    screening_queue = Submission.objects.filter(
        status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.TECHNICAL_CHECK]
    ).order_by('submission_date')
    desk_queue = Submission.objects.filter(status=SubmissionStatus.DESK_REVIEW).order_by('submission_date')
    under_review = Submission.objects.filter(status=SubmissionStatus.UNDER_REVIEW)
    revision_pending = Submission.objects.filter(status=SubmissionStatus.REVISION_REQUESTED)
    accepted = Submission.objects.filter(status=SubmissionStatus.ACCEPTED)
    return render(request, 'editorial/dashboard.html', {
        'screening_queue': screening_queue,
        'desk_queue': desk_queue,
        'under_review': under_review,
        'revision_pending': revision_pending,
        'accepted': accepted,
    })


@editorial_required
def submission_detail(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    revision = submission.get_current_revision()
    assignments = submission.assignments.filter(is_active=True)
    screening = submission.screening_checks.last()
    decisions = submission.editorial_decisions.all()
    from apps.reviewers.models import ReviewerSuggestion, ReviewerInvitation
    suggestions = ReviewerSuggestion.objects.filter(submission=submission)
    invitations = ReviewerInvitation.objects.filter(submission=submission)
    from apps.reviews.models import Review
    reviews = Review.objects.filter(invitation__submission=submission)
    return render(request, 'editorial/submission_detail.html', {
        'submission': submission,
        'revision': revision,
        'assignments': assignments,
        'screening': screening,
        'decisions': decisions,
        'suggestions': suggestions,
        'invitations': invitations,
        'reviews': reviews,
    })


@editorial_required
def record_screening(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if request.method == 'POST':
        check = ScreeningCheck.objects.create(
            submission=submission,
            checker=request.user,
            completeness_ok=bool(request.POST.get('completeness_ok')),
            scope_fit_ok=bool(request.POST.get('scope_fit_ok')),
            ethics_ok=bool(request.POST.get('ethics_ok')),
            notes=request.POST.get('notes', ''),
            result=request.POST.get('result', ''),
        )
        result = check.result
        if result == 'pass_to_desk':
            submission.status = SubmissionStatus.DESK_REVIEW
        elif result == 'return_to_author':
            submission.status = SubmissionStatus.SUBMITTED
        elif result == 'reject':
            submission.status = SubmissionStatus.DESK_REJECTED
        submission.save()
        messages.success(request, 'Screening saved.')
    return redirect('editorial_submission', pk=pk)


@editorial_required
def record_decision(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if request.method == 'POST':
        decision_type = request.POST.get('decision_type')
        round_num = submission.editorial_decisions.count() + 1
        decision = EditorialDecision.objects.create(
            submission=submission,
            round=round_num,
            decision_type=decision_type,
            editor=request.user,
            letter=request.POST.get('letter', ''),
            priority_issues=request.POST.get('priority_issues', ''),
            conflict_resolution_note=request.POST.get('conflict_resolution_note', ''),
            instructions_to_author=request.POST.get('instructions_to_author', ''),
            sent_at=timezone.now(),
        )
        # Update submission status
        status_map = {
            DecisionType.ACCEPT: SubmissionStatus.ACCEPTED,
            DecisionType.MINOR_REVISION: SubmissionStatus.REVISION_REQUESTED,
            DecisionType.MAJOR_REVISION: SubmissionStatus.REVISION_REQUESTED,
            DecisionType.REJECT: SubmissionStatus.REJECTED,
            DecisionType.DESK_REJECT: SubmissionStatus.DESK_REJECTED,
        }
        new_status = status_map.get(decision_type, submission.status)
        submission.status = new_status
        submission.save()
        from apps.notifications.tasks import notify_decision_sent
        notify_decision_sent.delay(decision.pk)
        messages.success(request, f'Decision recorded: {decision.get_decision_type_display()}')
    return redirect('editorial_submission', pk=pk)
