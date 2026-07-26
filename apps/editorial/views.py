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
            return render(request, '403.html', {'message': 'Editorial access required.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


@editorial_required
def editorial_dashboard(request):
    screening_queue = Submission.objects.filter(
        status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.TECHNICAL_CHECK]
    ).order_by('submission_date')
    desk_queue = Submission.objects.filter(status=SubmissionStatus.DESK_REVIEW).order_by('submission_date')
    under_review = Submission.objects.filter(
        status__in=[SubmissionStatus.UNDER_REVIEW, SubmissionStatus.REVISED]
    )
    revision_pending = Submission.objects.filter(
        status=SubmissionStatus.REVISION_REQUESTED
    ).order_by('updated_at')
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
@require_POST
def set_review_model(request):
    """Set the journal-wide peer-review blinding policy from the dashboard."""
    from apps.journal.models import JournalConfig
    choice = request.POST.get('review_model')
    if choice in ('double_blind', 'single_blind'):
        config = JournalConfig.get()
        config.review_model = choice
        config.save(update_fields=['review_model'])
        label = 'double-blind' if choice == 'double_blind' else 'single-blind'
        messages.success(request, f'Peer review is now {label}.')
    else:
        messages.error(request, 'Invalid review model.')
    return redirect('editorial_dashboard')


@editorial_required
def article_preview(request, pk):
    """Read-only rendering of a submission's manuscript for any editorial user.

    Lets editors and administrators read a submitted article from the editorial
    workbench without needing a reviewer invitation. The canonical document is
    built on demand (works for both uploaded .tex and editor-authored WYSIWYG
    submissions) if it does not exist yet.
    """
    submission = get_object_or_404(Submission, pk=pk)
    revision = submission.get_current_revision()

    canonical_doc_obj = None
    preview_error = None
    if revision:
        try:
            canonical_doc_obj = revision.canonical_document
        except Exception:
            canonical_doc_obj = None
        if canonical_doc_obj is None:
            # Build the canonical document on demand (handles .tex and WYSIWYG).
            try:
                from apps.production.tasks import ingest_submission
                ingest_submission(revision.pk)
                revision.refresh_from_db()
                try:
                    canonical_doc_obj = revision.canonical_document
                except Exception:
                    canonical_doc_obj = None
            except Exception as e:
                preview_error = str(e)

    article_html = None
    toc = []
    if canonical_doc_obj:
        from apps.documents.renderers.html_renderer import render_html, build_toc
        try:
            article_html = render_html(canonical_doc_obj.data, revision=revision,
                                       reviewer_mode=False)
            toc = build_toc(canonical_doc_obj.data)
        except Exception as e:
            preview_error = preview_error or str(e)

    return render(request, 'editorial/article_preview.html', {
        'submission': submission,
        'revision': revision,
        'article_html': article_html,
        'toc': toc,
        'preview_error': preview_error,
    })


@editorial_required
def submission_detail(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    revision = submission.get_current_revision()
    assignments = submission.assignments.filter(is_active=True)
    screenings = submission.screening_checks.order_by('checked_at')
    latest_screening = screenings.last()
    # Show the screening form when there is no check yet, or when the author
    # has resubmitted a correction after the most recent check (the revision's
    # submitted_at is newer than the last screening check's checked_at).
    needs_screening = submission.status == SubmissionStatus.SUBMITTED and (
        latest_screening is None
        or (
            revision
            and revision.submitted_at
            and revision.submitted_at > latest_screening.checked_at
        )
    )
    decisions = submission.editorial_decisions.all()
    from apps.reviewers.models import ReviewerSuggestion, ReviewerInvitation
    suggestions = ReviewerSuggestion.objects.filter(submission=submission)
    invitations = ReviewerInvitation.objects.filter(submission=submission)
    from apps.reviews.models import Review
    reviews = (
        Review.objects
        .filter(invitation__submission=submission)
        .select_related('invitation', 'invitation__reviewer', 'revision')
        .prefetch_related('annotations')
        .order_by('invitation__sent_at')
    )
    # Production state
    build = None
    canonical_doc = None
    if revision:
        try:
            canonical_doc = revision.canonical_document
            build = getattr(canonical_doc, 'html_build', None)
        except Exception:
            pass

    default_deadline = (timezone.now().date() + timezone.timedelta(days=60)).isoformat()

    from apps.notifications.models import AuditEvent
    audit_events = AuditEvent.objects.filter(submission=submission).order_by('-timestamp')

    return render(request, 'editorial/submission_detail.html', {
        'submission': submission,
        'revision': revision,
        'assignments': assignments,
        'screenings': screenings,
        'needs_screening': needs_screening,
        'decisions': decisions,
        'suggestions': suggestions,
        'invitations': invitations,
        'reviews': reviews,
        'build': build,
        'canonical_doc': canonical_doc,
        'default_deadline': default_deadline,
        'audit_events': audit_events,
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
        if result == 'return_to_author':
            from apps.notifications.tasks import notify_returned_to_author
            notify_returned_to_author(submission.pk)
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
        # If requesting revisions on a live article, take it off the public site first
        revision_decisions = (DecisionType.MINOR_REVISION, DecisionType.MAJOR_REVISION,
                              DecisionType.REJECT_RESUBMIT)
        if decision_type in revision_decisions and submission.status == SubmissionStatus.PUBLISHED:
            try:
                build = submission.get_current_revision().canonical_document.html_build
                build.is_published = False
                build.published_at = None
                build.save(update_fields=['is_published', 'published_at'])
            except Exception:
                pass  # no HTMLBuild — nothing to unpublish

        # Update submission status
        status_map = {
            DecisionType.ACCEPT: SubmissionStatus.ACCEPTED,
            DecisionType.MINOR_REVISION: SubmissionStatus.REVISION_REQUESTED,
            DecisionType.MAJOR_REVISION: SubmissionStatus.REVISION_REQUESTED,
            DecisionType.REJECT_RESUBMIT: SubmissionStatus.REVISION_REQUESTED,
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

    # Deactivate any existing assignment for this submission + role, notifying displaced editors.
    displaced = list(
        EditorialAssignment.objects.filter(
            submission=submission, role=role, is_active=True
        ).select_related('editor')
    )
    EditorialAssignment.objects.filter(
        submission=submission, role=role, is_active=True
    ).update(is_active=False)

    asgn = EditorialAssignment.objects.create(
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
    role_label = asgn.get_role_display()
    messages.success(request, f'{editor.display_name} assigned as {role_label}.')

    from apps.notifications.tasks import notify_editor_assigned, notify_editor_removed
    notify_editor_assigned(asgn.pk)
    for prev in displaced:
        if prev.editor and prev.editor != editor:
            notify_editor_removed(prev.editor.pk, submission.title, role_label)

    return redirect('editorial_submission', pk=submission_pk)


@editorial_required
@require_POST
def remove_editor(request, submission_pk, assignment_pk):
    """Remove (deactivate) an editorial assignment."""
    submission = get_object_or_404(Submission, pk=submission_pk)
    asgn = get_object_or_404(EditorialAssignment, pk=assignment_pk, submission=submission, is_active=True)

    editor_pk = asgn.editor.pk if asgn.editor else None
    role_label = asgn.get_role_display()

    asgn.is_active = False
    asgn.save(update_fields=['is_active'])

    from apps.notifications.models import AuditEvent
    AuditEvent.objects.create(
        submission=submission,
        actor=request.user,
        event_type='editor_removed',
        payload={'note': f'{request.user.display_name} removed {asgn.editor.display_name if asgn.editor else "editor"} ({role_label})'},
    )
    messages.success(request, f'{asgn.editor.display_name if asgn.editor else "Editor"} removed.')

    if editor_pk:
        from apps.notifications.tasks import notify_editor_removed
        notify_editor_removed(editor_pk, submission.title, role_label)

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


@editorial_required
@require_POST
def reinvite_reviewer(request, pk, reviewer_pk):
    """Create a fresh invitation for a previous-round reviewer on a revised submission."""
    from apps.accounts.models import User
    from apps.reviewers.models import ReviewerInvitation
    from apps.submissions.models import SubmissionStatus

    submission = get_object_or_404(Submission, pk=pk)
    reviewer = get_object_or_404(User, pk=reviewer_pk)

    deadline_str = request.POST.get('deadline')
    try:
        from datetime import date
        deadline = date.fromisoformat(deadline_str) if deadline_str else (
            timezone.now().date() + timezone.timedelta(days=60)
        )
    except ValueError:
        deadline = timezone.now().date() + timezone.timedelta(days=60)

    inv = ReviewerInvitation.objects.create(
        submission=submission,
        reviewer=reviewer,
        deadline=deadline,
    )

    from apps.notifications.tasks import notify_reviewer_invited
    notify_reviewer_invited(inv.pk)

    # Transition from revised → under_review now that we're actively re-inviting
    if submission.status == SubmissionStatus.REVISED:
        submission.status = SubmissionStatus.UNDER_REVIEW
        submission.save()

    from apps.notifications.models import AuditEvent
    AuditEvent.objects.create(
        submission=submission,
        actor=request.user,
        event_type='reviewer_reinvited',
        payload={'note': f'{reviewer.display_name} re-invited for revised submission'},
    )

    messages.success(request, f'{reviewer.display_name} has been re-invited (deadline {deadline}).')
    return redirect('editorial_submission', pk=pk)
