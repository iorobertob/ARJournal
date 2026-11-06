"""
Governance section — meeting minutes, submission reports, per-call planning,
handling-editor / reviewer assignment (internal, no emails), and an editable
milestone timeline.

Access: admins + senior editors (same gate as the journal admin dashboard) plus
any user explicitly granted `governance_access`. Rendered inside the journal
admin shell.
"""
import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User, UserRole
from apps.journal.models import Call, Issue, NewsPost
from apps.journal.sanitize import sanitize_html
from apps.submissions.models import Submission, SubmissionStatus
from .models import Meeting, Milestone, MilestoneKind, ReviewerPlan


# --------------------------------------------------------------------------- #
# Access control
# --------------------------------------------------------------------------- #

def governance_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.has_governance_access():
            return render(request, '403.html',
                          {'message': 'Governance access required.'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper


# Editorial roles eligible to be handling editors.
_EDITOR_ROLES = [
    UserRole.HANDLING_EDITOR, UserRole.ASSOCIATE_EDITOR, UserRole.GUEST_EDITOR,
    UserRole.MANAGING_EDITOR, UserRole.EDITOR_IN_CHIEF, UserRole.EDITORIAL_ASSISTANT,
]


def _editor_candidates():
    q = Q()
    for role in _EDITOR_ROLES:
        q |= Q(roles__contains=role)
    return User.objects.filter(q).order_by('first_name', 'last_name', 'email')


def _reviewer_candidates():
    return User.objects.filter(
        roles__contains=UserRole.REVIEWER,
    ).order_by('first_name', 'last_name', 'email')


# --------------------------------------------------------------------------- #
# Report helpers
# --------------------------------------------------------------------------- #

def _filter_submissions(request):
    """Return (queryset, filters-dict) for the submissions report, applying the
    call / issue / year / status / discipline / date-range GET filters."""
    qs = (Submission.objects
          .exclude(status=SubmissionStatus.DRAFT)
          .select_related('author', 'issue', 'call')
          .order_by('-submission_date', '-created_at'))

    f = {
        'call': request.GET.get('call', '').strip(),
        'issue': request.GET.get('issue', '').strip(),
        'year': request.GET.get('year', '').strip(),
        'status': request.GET.get('status', '').strip(),
        'discipline': request.GET.get('discipline', '').strip(),
        'date_from': request.GET.get('date_from', '').strip(),
        'date_to': request.GET.get('date_to', '').strip(),
        'q': request.GET.get('q', '').strip(),
    }

    if f['call'] == 'none':
        qs = qs.filter(call__isnull=True)
    elif f['call']:
        qs = qs.filter(call__pk=f['call'])
    if f['issue']:
        qs = qs.filter(issue__pk=f['issue'])
    if f['year']:
        qs = qs.filter(
            Q(submission_date__year=f['year']) |
            Q(submission_date__isnull=True, created_at__year=f['year'])
        )
    if f['status']:
        qs = qs.filter(status=f['status'])
    if f['discipline']:
        qs = qs.filter(disciplines__contains=[f['discipline']])
    if f['date_from']:
        qs = qs.filter(created_at__date__gte=f['date_from'])
    if f['date_to']:
        qs = qs.filter(created_at__date__lte=f['date_to'])
    if f['q']:
        qs = qs.filter(
            Q(title__icontains=f['q']) |
            Q(author__first_name__icontains=f['q']) |
            Q(author__last_name__icontains=f['q']) |
            Q(author__email__icontains=f['q'])
        ).distinct()

    return qs, f


def _effective_date(sub):
    return sub.submission_date or sub.created_at


def _aggregate(qs):
    """Build the report aggregates. Disciplines live in a JSON list so they are
    tallied in Python; the rest use DB aggregation."""
    subs = list(qs)
    total = len(subs)

    status_labels = dict(SubmissionStatus.choices)
    by_status, by_call, by_issue, by_year, by_discipline = {}, {}, {}, {}, {}

    for s in subs:
        by_status[s.status] = by_status.get(s.status, 0) + 1
        call_name = s.call.title if s.call else 'Unassigned'
        by_call[call_name] = by_call.get(call_name, 0) + 1
        issue_name = str(s.issue) if s.issue else 'No issue'
        by_issue[issue_name] = by_issue.get(issue_name, 0) + 1
        year = _effective_date(s).year
        by_year[year] = by_year.get(year, 0) + 1
        for d in (s.disciplines or []):
            by_discipline[d] = by_discipline.get(d, 0) + 1

    def rows(d, label_map=None, sort_by_key=False):
        items = d.items()
        if sort_by_key:
            items = sorted(items, key=lambda kv: kv[0])
        else:
            items = sorted(items, key=lambda kv: (-kv[1], str(kv[0])))
        maxc = max(d.values()) if d else 0
        out = []
        for k, v in items:
            label = label_map.get(k, k) if label_map else k
            pct = round(v * 100 / total) if total else 0
            out.append({'label': label, 'count': v, 'pct': pct})
        return {'rows': out, 'max': maxc}

    return {
        'total': total,
        'by_status': rows(by_status, status_labels),
        'by_call': rows(by_call),
        'by_issue': rows(by_issue),
        'by_year': rows(by_year, sort_by_key=True),
        'by_discipline': rows(by_discipline),
    }


def _filter_context(request):
    return {
        'calls': Call.objects.all(),
        'issues': Issue.objects.order_by('-year', '-number'),
        'statuses': SubmissionStatus.choices,
        'years': sorted(
            {d.year for d in Submission.objects.exclude(status=SubmissionStatus.DRAFT)
             .values_list('created_at', flat=True)},
            reverse=True,
        ),
    }


# --------------------------------------------------------------------------- #
# Overview + report
# --------------------------------------------------------------------------- #

@governance_required
def home(request):
    qs, f = _filter_submissions(request)
    agg = _aggregate(qs)
    ctx = {
        'agg': agg,
        'submissions': qs[:200],
        'submissions_truncated': agg['total'] > 200,
        'filters': f,
        'query_string': request.GET.urlencode(),
        'open_actions_count': Milestone.objects.filter(
            due_date__gte=timezone.now().date()).count(),
        'meetings_count': Meeting.objects.count(),
        'calls_count': Call.objects.count(),
    }
    ctx.update(_filter_context(request))
    return render(request, 'journal_admin/governance/home.html', ctx)


@governance_required
def report_csv(request):
    qs, _f = _filter_submissions(request)
    response = HttpResponse(content_type='text/csv')
    stamp = timezone.now().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="submissions-report-{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Topic / Title', 'Author', 'Disciplines', 'Keywords',
                     'Call', 'Issue', 'Status', 'Submitted'])
    for s in qs:
        writer.writerow([
            s.pk,
            s.title,
            s.author.display_name if s.author else '',
            '; '.join(s.disciplines or []),
            '; '.join(s.keywords or []),
            s.call.title if s.call else '',
            str(s.issue) if s.issue else '',
            s.get_status_display(),
            _effective_date(s).strftime('%Y-%m-%d') if _effective_date(s) else '',
        ])
    return response


@governance_required
def report_pdf(request):
    qs, f = _filter_submissions(request)
    agg = _aggregate(qs)
    from apps.journal.models import JournalConfig
    html = render(request, 'journal_admin/governance/report_pdf.html', {
        'agg': agg,
        'submissions': qs,
        'filters': f,
        'journal': JournalConfig.get(),
        'generated_at': timezone.now(),
    }).content.decode('utf-8')

    import sys
    import os
    if sys.platform == 'darwin':
        brew_lib = '/opt/homebrew/lib'
        dyld = os.environ.get('DYLD_LIBRARY_PATH', '')
        if brew_lib not in dyld:
            os.environ['DYLD_LIBRARY_PATH'] = f'{brew_lib}:{dyld}' if dyld else brew_lib
    try:
        from weasyprint import HTML
    except Exception:
        messages.error(request,
                        'PDF export needs WeasyPrint system libraries (Pango/Cairo). '
                        'Use CSV export, or install them (see CLAUDE.md).')
        return redirect(f"{reverse('governance_home')}?{request.GET.urlencode()}")

    pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    stamp = timezone.now().strftime('%Y%m%d')
    response['Content-Disposition'] = f'inline; filename="submissions-report-{stamp}.pdf"'
    return response


# --------------------------------------------------------------------------- #
# Submissions management (assign call / handling editor / planned reviewers)
# --------------------------------------------------------------------------- #

@governance_required
def submission_list(request):
    if request.method == 'POST':
        return _handle_submission_action(request)

    qs, f = _filter_submissions(request)
    qs = qs.prefetch_related('assignments__editor', 'reviewer_plans__reviewer')

    from apps.editorial.models import EditorialAssignment  # noqa: F401 (referenced via relation)
    rows = []
    for s in qs[:300]:
        handling = next(
            (a for a in s.assignments.all()
             if a.role == 'handling_editor' and a.is_active), None)
        rows.append({
            'sub': s,
            'handling_editor': handling.editor if handling else None,
            'reviewer_plans': list(s.reviewer_plans.all()),
        })

    ctx = {
        'rows': rows,
        'filters': f,
        'editor_candidates': _editor_candidates(),
        'reviewer_candidates': _reviewer_candidates(),
        'query_string': request.GET.urlencode(),
    }
    ctx.update(_filter_context(request))
    return render(request, 'journal_admin/governance/submission_list.html', ctx)


def _redirect_back(request):
    qs = request.POST.get('return_qs', '')
    base = reverse('governance_submissions')
    return redirect(f'{base}?{qs}' if qs else base)


def _handle_submission_action(request):
    action = request.POST.get('action', '')
    submission = get_object_or_404(Submission, pk=request.POST.get('submission_id'))

    from apps.editorial.models import EditorialAssignment
    from apps.notifications.models import AuditEvent

    if action == 'set_call':
        call_id = request.POST.get('call_id', '')
        if call_id:
            submission.call = get_object_or_404(Call, pk=call_id)
        else:
            submission.call = None
        submission.save(update_fields=['call'])
        AuditEvent.objects.create(
            submission=submission, actor=request.user, event_type='governance_call_set',
            payload={'note': f'Call set to {submission.call.title if submission.call else "none"}'},
        )
        messages.success(request, f'Call updated for “{submission.title[:50]}”.')

    elif action == 'set_handling_editor':
        editor_id = request.POST.get('editor_id', '')
        # Deactivate current handling editor(s) — no notifications (internal only).
        EditorialAssignment.objects.filter(
            submission=submission, role='handling_editor', is_active=True,
        ).update(is_active=False)
        if editor_id:
            editor = get_object_or_404(User, pk=editor_id)
            EditorialAssignment.objects.create(
                submission=submission, editor=editor, role='handling_editor',
            )
            AuditEvent.objects.create(
                submission=submission, actor=request.user,
                event_type='governance_handling_editor_set',
                payload={'note': f'{request.user.display_name} set handling editor '
                                 f'{editor.display_name} (governance, no email)'},
            )
            messages.success(request, f'{editor.display_name} set as handling editor.')
        else:
            messages.success(request, 'Handling editor cleared.')

    elif action == 'add_reviewer_plan':
        reviewer_id = request.POST.get('reviewer_id', '')
        if not reviewer_id:
            return _redirect_back(request)
        reviewer = get_object_or_404(User, pk=reviewer_id)
        _, created = ReviewerPlan.objects.get_or_create(
            submission=submission, reviewer=reviewer,
            defaults={'created_by': request.user,
                      'note': request.POST.get('note', '').strip()[:500]},
        )
        if created:
            messages.success(request, f'{reviewer.display_name} added as a planned reviewer.')
        else:
            messages.info(request, f'{reviewer.display_name} is already planned.')

    elif action == 'remove_reviewer_plan':
        ReviewerPlan.objects.filter(
            submission=submission, pk=request.POST.get('plan_id'),
        ).delete()
        messages.success(request, 'Planned reviewer removed.')

    else:
        return HttpResponseBadRequest('Unknown action.')

    return _redirect_back(request)


# --------------------------------------------------------------------------- #
# Calls
# --------------------------------------------------------------------------- #

@governance_required
def call_list(request):
    calls = Call.objects.annotate(n_subs=Count('submissions')).all()
    return render(request, 'journal_admin/governance/call_list.html', {'calls': calls})


@governance_required
def call_edit(request, pk=None):
    call = get_object_or_404(Call, pk=pk) if pk else None
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'A title is required.')
            return redirect(request.path)
        if call is None:
            call = Call()
        call.title = title
        call.description = sanitize_html(request.POST.get('description', ''))
        call.opens_at = request.POST.get('opens_at') or None
        call.closes_at = request.POST.get('closes_at') or None
        call.is_active = request.POST.get('is_active') == 'on'
        issue_id = request.POST.get('issue_id', '')
        news_id = request.POST.get('news_id', '')
        call.issue = Issue.objects.filter(pk=issue_id).first() if issue_id else None
        call.news_post = NewsPost.objects.filter(pk=news_id).first() if news_id else None
        call.save()
        messages.success(request, f'Call “{call.title}” saved.')
        return redirect('governance_calls')

    return render(request, 'journal_admin/governance/call_form.html', {
        'call': call,
        'issues': Issue.objects.order_by('-year', '-number'),
        'news_posts': NewsPost.objects.all(),
    })


@governance_required
@require_POST
def call_delete(request, pk):
    call = get_object_or_404(Call, pk=pk)
    # SET_NULL on submissions keeps them intact; just detach.
    title = call.title
    call.delete()
    messages.success(request, f'Call “{title}” deleted. Its submissions were kept (now unassigned).')
    return redirect('governance_calls')


# --------------------------------------------------------------------------- #
# Meetings / minutes
# --------------------------------------------------------------------------- #

@governance_required
def meeting_list(request):
    meetings = Meeting.objects.prefetch_related('attendees').all()
    return render(request, 'journal_admin/governance/meeting_list.html', {'meetings': meetings})


@governance_required
def meeting_edit(request, pk=None):
    meeting = get_object_or_404(Meeting, pk=pk) if pk else None
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        meeting_date = request.POST.get('meeting_date') or None
        if not title or not meeting_date:
            messages.error(request, 'Title and meeting date are required.')
            return redirect(request.path)
        if meeting is None:
            meeting = Meeting(created_by=request.user)
        meeting.title = title
        meeting.team_label = request.POST.get('team_label', '').strip()
        meeting.meeting_date = meeting_date
        meeting.minutes = sanitize_html(request.POST.get('minutes', ''))
        meeting.save()
        attendee_ids = request.POST.getlist('attendees')
        meeting.attendees.set(User.objects.filter(pk__in=attendee_ids))
        messages.success(request, f'Minutes for “{meeting.title}” saved.')
        return redirect('governance_meetings')

    return render(request, 'journal_admin/governance/meeting_form.html', {
        'meeting': meeting,
        'users': User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'email'),
        'selected_ids': set(meeting.attendees.values_list('pk', flat=True)) if meeting else set(),
    })


@governance_required
@require_POST
def meeting_delete(request, pk):
    meeting = get_object_or_404(Meeting, pk=pk)
    title = meeting.title
    meeting.delete()
    messages.success(request, f'Meeting “{title}” deleted.')
    return redirect('governance_meetings')


# --------------------------------------------------------------------------- #
# Timeline / milestones
# --------------------------------------------------------------------------- #

@governance_required
def timeline(request):
    if request.method == 'POST':
        return _handle_milestone_action(request)

    calls = Call.objects.prefetch_related('milestones').all()
    issues = Issue.objects.prefetch_related('milestones').order_by('-year', '-number')
    # Only show issues that actually have milestones, plus all calls.
    issues_with = [i for i in issues if i.milestones.exists()]
    return render(request, 'journal_admin/governance/timeline.html', {
        'calls': calls,
        'issues_with': issues_with,
        'all_issues': issues,
        'kinds': MilestoneKind.choices,
        'today': timezone.now().date(),
    })


def _handle_milestone_action(request):
    action = request.POST.get('action', '')

    if action == 'add':
        # `target` is "call:<pk>" or "issue:<pk>".
        target = request.POST.get('target', '')
        m = Milestone(
            kind=request.POST.get('kind', MilestoneKind.CUSTOM),
            label=request.POST.get('label', '').strip(),
            due_date=request.POST.get('due_date') or None,
            note=request.POST.get('note', '').strip(),
        )
        if target.startswith('call:'):
            m.call = get_object_or_404(Call, pk=target.split(':', 1)[1])
        elif target.startswith('issue:'):
            m.issue = get_object_or_404(Issue, pk=target.split(':', 1)[1])
        else:
            messages.error(request, 'Pick a call or an issue for the milestone.')
            return redirect('governance_timeline')
        m.save()
        messages.success(request, 'Milestone added.')

    elif action == 'edit':
        m = get_object_or_404(Milestone, pk=request.POST.get('milestone_id'))
        m.kind = request.POST.get('kind', m.kind)
        m.label = request.POST.get('label', '').strip()
        m.due_date = request.POST.get('due_date') or None
        m.note = request.POST.get('note', '').strip()
        m.save()
        messages.success(request, 'Milestone updated.')

    elif action == 'delete':
        Milestone.objects.filter(pk=request.POST.get('milestone_id')).delete()
        messages.success(request, 'Milestone deleted.')

    else:
        return HttpResponseBadRequest('Unknown action.')

    return redirect('governance_timeline')


# --------------------------------------------------------------------------- #
# Access management
# --------------------------------------------------------------------------- #

@governance_required
def access(request):
    can_grant = request.user.can_grant_governance_access()
    if request.method == 'POST':
        if not can_grant:
            return render(request, '403.html',
                          {'message': 'Only admins / senior editors can change access.'},
                          status=403)
        target = get_object_or_404(User, pk=request.POST.get('user_id'))
        # Back-compat: older forms sent grant=1/0 instead of an explicit action.
        action = request.POST.get('action') or (
            'grant' if request.POST.get('grant') == '1' else 'revoke')

        # Role-based access (block/unblock) can never be changed for yourself or a
        # superuser — that guards against anyone locking out the site owner.
        if action in ('block', 'unblock') and (
                target.pk == request.user.pk or target.is_superuser):
            messages.error(
                request,
                "You can't change role-based governance access for yourself or a "
                "superuser.")
            return redirect('governance_access')

        if action == 'grant':
            if target.has_journal_admin_access():
                messages.info(
                    request, f'{target.display_name} already has access via their role.')
            else:
                target.governance_access = True
                target.save(update_fields=['governance_access'])
                messages.success(
                    request, f'Governance access granted to {target.display_name}.')
        elif action == 'revoke':
            target.governance_access = False
            target.save(update_fields=['governance_access'])
            messages.success(
                request, f'Governance access revoked from {target.display_name}.')
        elif action == 'block':
            target.governance_blocked = True
            target.save(update_fields=['governance_blocked'])
            messages.success(
                request,
                f'Governance access revoked from {target.display_name}. They keep their '
                f'other roles but can no longer open or edit the Governance section.')
        elif action == 'unblock':
            target.governance_blocked = False
            target.save(update_fields=['governance_blocked'])
            messages.success(
                request,
                f'Governance access restored for {target.display_name} (via their role).')
        else:
            return HttpResponseBadRequest('Unknown action.')
        return redirect('governance_access')

    granted = User.objects.filter(governance_access=True).order_by(
        'first_name', 'last_name', 'email')
    # Candidates to grant: active non-admin users not already granted.
    candidates = [
        u for u in User.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'email')
        if not u.has_journal_admin_access() and not u.governance_access
    ]
    role_based = [
        u for u in User.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'email')
        if u.has_journal_admin_access()
    ]
    return render(request, 'journal_admin/governance/access.html', {
        'granted': granted,
        'candidates': candidates,
        'role_based': role_based,
        'can_grant': can_grant,
    })
