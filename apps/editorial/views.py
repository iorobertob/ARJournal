from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
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

    # Submissions this editor is actively supervising
    my_assignments = (
        EditorialAssignment.objects
        .filter(editor=request.user, is_active=True)
        .select_related('submission', 'submission__author')
        .order_by('-assigned_at')
    )

    # Full assignment history for this editor (for the history panel)
    my_assignment_history = (
        EditorialAssignment.objects
        .filter(editor=request.user)
        .select_related('submission', 'submission__author')
        .order_by('-assigned_at')
    )

    return render(request, 'editorial/dashboard.html', {
        'screening_queue': screening_queue,
        'desk_queue': desk_queue,
        'under_review': under_review,
        'revision_pending': revision_pending,
        'accepted': accepted,
        'my_assignments': my_assignments,
        'my_assignment_history': my_assignment_history,
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
    # Production state
    build = None
    canonical_doc = None
    if revision:
        try:
            canonical_doc = revision.canonical_document
            build = getattr(canonical_doc, 'html_build', None)
        except Exception:
            pass

    return render(request, 'editorial/submission_detail.html', {
        'submission': submission,
        'revision': revision,
        'assignments': assignments,
        'screening': screening,
        'decisions': decisions,
        'suggestions': suggestions,
        'invitations': invitations,
        'reviews': reviews,
        'build': build,
        'canonical_doc': canonical_doc,
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
        notify_decision_sent(decision.pk)
        messages.success(request, f'Decision recorded: {decision.get_decision_type_display()}')
    return redirect('editorial_submission', pk=pk)


@editorial_required
@require_POST
def assign_editor(request, submission_pk):
    """Assign an editor to supervise the review process for a submission."""
    submission = get_object_or_404(Submission, pk=submission_pk)
    from apps.accounts.models import User
    editor = get_object_or_404(User, pk=request.POST.get('editor_id'))
    role = request.POST.get('role', 'handling_editor')

    # Deactivate any existing assignment for this submission + role
    EditorialAssignment.objects.filter(
        submission=submission, role=role, is_active=True
    ).update(is_active=False)

    EditorialAssignment.objects.create(
        submission=submission,
        editor=editor,
        role=role,
    )

    from apps.notifications.models import AuditEvent
    AuditEvent.objects.create(
        submission=submission,
        actor=request.user,
        event_type='editor_assigned',
        payload={'note': f'{request.user.display_name} assigned {editor.display_name} as {role}'},
    )
    asgn = EditorialAssignment.objects.filter(submission=submission, editor=editor, is_active=True).last()
    role_label = asgn.get_role_display() if asgn else role
    messages.success(request, f'{editor.display_name} assigned as {role_label}.')
    return redirect('editorial_submission', pk=submission_pk)


@editorial_required
def editor_search_json(request, submission_pk):
    """Autocomplete JSON endpoint: returns editorial users matching ?q= query."""
    from apps.accounts.models import User, UserRole
    from django.db.models import Q
    get_object_or_404(Submission, pk=submission_pk)  # access check
    q = request.GET.get('q', '').strip()

    qs = User.objects.filter(
        Q(roles__contains=UserRole.HANDLING_EDITOR) |
        Q(roles__contains=UserRole.MANAGING_EDITOR) |
        Q(roles__contains=UserRole.EDITOR_IN_CHIEF) |
        Q(roles__contains=UserRole.EDITORIAL_ASSISTANT),
        is_active=True,
    )
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).distinct()

    results = [
        {
            'id': u.pk,
            'name': u.display_name,
            'email': u.email,
            'roles': ', '.join(u.get_roles_display()),
        }
        for u in qs[:30]
    ]
    return JsonResponse({'results': results})
