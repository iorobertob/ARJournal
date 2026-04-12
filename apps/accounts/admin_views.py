"""
Journal Admin views — custom platform administration (not Django admin).
Accessible to users with role journal_admin or system_admin, or is_superuser.
Also includes issue/volume assembly for the editor-in-chief.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Q

from .models import User, UserRole


def journal_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.has_role(
                UserRole.JOURNAL_ADMIN, UserRole.SYSTEM_ADMIN,
                UserRole.EDITOR_IN_CHIEF, UserRole.MANAGING_EDITOR,
            )
        ):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden('Journal admin access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


@journal_admin_required
def dashboard(request):
    from apps.submissions.models import Submission, SubmissionStatus
    from apps.journal.models import JournalConfig, Issue

    stats = {
        'users': User.objects.count(),
        'submissions_total': Submission.objects.count(),
        'submissions_active': Submission.objects.exclude(
            status__in=[SubmissionStatus.PUBLISHED, SubmissionStatus.REJECTED, SubmissionStatus.DESK_REJECTED]
        ).count(),
        'reviewers': User.objects.filter(roles__contains=UserRole.REVIEWER).count(),
        'published': Submission.objects.filter(status=SubmissionStatus.PUBLISHED).count(),
        'issues': Issue.objects.count(),
    }
    # Count users per role by unnesting the roles JSON array
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT role_value, COUNT(*) as cnt
            FROM accounts_user, jsonb_array_elements_text(roles) AS role_value
            GROUP BY role_value ORDER BY role_value
        """)
        users_by_role = [{'role': row[0], 'count': row[1]} for row in cursor.fetchall()]
    recent_users = User.objects.order_by('-date_joined')[:10]
    journal = JournalConfig.get()
    return render(request, 'journal_admin/dashboard.html', {
        'stats': stats,
        'users_by_role': users_by_role,
        'recent_users': recent_users,
        'journal': journal,
    })


@journal_admin_required
def user_list(request):
    role_filter = request.GET.get('role', '')
    search = request.GET.get('q', '')
    users = User.objects.order_by('email')
    if role_filter:
        users = users.filter(roles__contains=role_filter)
    if search:
        users = users.filter(email__icontains=search) | User.objects.filter(
            first_name__icontains=search
        ) | User.objects.filter(last_name__icontains=search)
        users = users.distinct()
    return render(request, 'journal_admin/user_list.html', {
        'users': users,
        'roles': UserRole.choices,
        'role_filter': role_filter,
        'search': search,
    })


@journal_admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        valid_roles = dict(UserRole.choices)
        selected_roles = [r for r in request.POST.getlist('roles') if r in valid_roles]
        if not selected_roles:
            selected_roles = [UserRole.AUTHOR]
        user.roles = selected_roles
        user.is_active = bool(request.POST.get('is_active'))
        user.save(update_fields=['roles', 'is_active'])
        messages.success(request, f'Roles updated for {user.email}.')
        return redirect('journal_admin_users')
    return render(request, 'journal_admin/user_edit.html', {
        'edited_user': user,
        'roles': UserRole.choices,
    })


@journal_admin_required
def journal_settings(request):
    from apps.journal.models import JournalConfig
    journal = JournalConfig.get()
    if request.method == 'POST':
        # Identity
        journal.name = request.POST.get('name', journal.name)
        journal.tagline = request.POST.get('tagline', journal.tagline)
        journal.issn_print = request.POST.get('issn_print', journal.issn_print)
        journal.issn_online = request.POST.get('issn_online', journal.issn_online)
        journal.description = request.POST.get('description', journal.description)
        journal.contact_email = request.POST.get('contact_email', journal.contact_email)
        journal.editorial_email = request.POST.get('editorial_email', journal.editorial_email)
        journal.submission_open = bool(request.POST.get('submission_open'))
        if request.FILES.get('logo'):
            journal.logo = request.FILES['logo']
        # Email
        journal.email_from_name = request.POST.get('email_from_name', journal.email_from_name)
        journal.email_from_address = request.POST.get('email_from_address', journal.email_from_address)
        journal.mailersend_api_token = request.POST.get('mailersend_api_token', journal.mailersend_api_token)
        # ORCID
        journal.orcid_enabled = bool(request.POST.get('orcid_enabled'))
        journal.orcid_client_id = request.POST.get('orcid_client_id', journal.orcid_client_id)
        journal.orcid_client_secret = request.POST.get('orcid_client_secret', journal.orcid_client_secret)
        # Crossref / DOI
        journal.doi_enabled = bool(request.POST.get('doi_enabled'))
        journal.doi_prefix = request.POST.get('doi_prefix', journal.doi_prefix)
        journal.crossref_login = request.POST.get('crossref_login', journal.crossref_login)
        journal.crossref_password = request.POST.get('crossref_password', journal.crossref_password)
        journal.crossref_depositor_name = request.POST.get('crossref_depositor_name', journal.crossref_depositor_name)
        journal.crossref_depositor_email = request.POST.get('crossref_depositor_email', journal.crossref_depositor_email)
        # Turnitin
        journal.turnitin_enabled = bool(request.POST.get('turnitin_enabled'))
        journal.turnitin_api_key = request.POST.get('turnitin_api_key', journal.turnitin_api_key)
        journal.turnitin_base_url = request.POST.get('turnitin_base_url', journal.turnitin_base_url)
        # AI
        journal.ai_features_enabled = bool(request.POST.get('ai_features_enabled'))
        journal.openai_api_key = request.POST.get('openai_api_key', journal.openai_api_key)
        journal.save()
        messages.success(request, 'Journal settings saved.')
        return redirect('journal_admin_settings')
    return render(request, 'journal_admin/settings.html', {'journal': journal})


# ── Issue & Volume Assembly ──────────────────────────────────────

@journal_admin_required
def issue_list(request):
    from apps.journal.models import Issue
    issues = Issue.objects.annotate(
        article_count=Count('submissions')
    ).order_by('-year', '-number')
    return render(request, 'journal_admin/issue_list.html', {'issues': issues})


@journal_admin_required
def issue_create(request):
    from apps.journal.models import Issue
    if request.method == 'POST':
        issue = Issue.objects.create(
            number=int(request.POST.get('number', 1)),
            volume=int(request.POST.get('volume', 1)),
            year=int(request.POST.get('year', 2026)),
            title=request.POST.get('title', ''),
            editorial_note=request.POST.get('editorial_note', ''),
            call_for_submissions=request.POST.get('call_for_submissions', ''),
        )
        if request.FILES.get('cover_image'):
            issue.cover_image = request.FILES['cover_image']
            issue.save()
        messages.success(request, f'Issue #{issue.number} created.')
        return redirect('journal_admin_issue_edit', pk=issue.pk)
    # Suggest next number
    last = Issue.objects.order_by('-number').first()
    next_number = (last.number + 1) if last else 1
    next_volume = last.volume if last else 1
    return render(request, 'journal_admin/issue_form.html', {
        'next_number': next_number,
        'next_volume': next_volume,
    })


@journal_admin_required
def issue_edit(request, pk):
    from apps.journal.models import Issue, Section
    from apps.submissions.models import Submission, SubmissionStatus
    issue = get_object_or_404(Issue, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'save':
            issue.number = int(request.POST.get('number', issue.number))
            issue.volume = int(request.POST.get('volume', issue.volume))
            issue.year = int(request.POST.get('year', issue.year))
            issue.title = request.POST.get('title', issue.title)
            issue.editorial_note = request.POST.get('editorial_note', issue.editorial_note)
            issue.call_for_submissions = request.POST.get('call_for_submissions', '')
            issue.is_current = bool(request.POST.get('is_current'))
            if request.FILES.get('cover_image'):
                issue.cover_image = request.FILES['cover_image']
            issue.save()
            messages.success(request, 'Issue updated.')

        elif action == 'add_article':
            submission_pk = request.POST.get('submission_pk')
            if submission_pk:
                sub = get_object_or_404(Submission, pk=submission_pk)
                sub.issue = issue
                max_order = issue.submissions.aggregate(
                    m=Count('id'))['m'] or 0
                sub.issue_order = max_order
                sub.save(update_fields=['issue', 'issue_order'])
                messages.success(request, f'Added "{sub.title[:40]}…" to this issue.')

        elif action == 'remove_article':
            submission_pk = request.POST.get('submission_pk')
            if submission_pk:
                sub = get_object_or_404(Submission, pk=submission_pk)
                sub.issue = None
                sub.issue_order = 0
                sub.save(update_fields=['issue', 'issue_order'])
                messages.success(request, f'Removed article from this issue.')

        elif action == 'reorder':
            order_data = request.POST.getlist('order[]')
            for idx, sub_pk in enumerate(order_data):
                Submission.objects.filter(pk=sub_pk, issue=issue).update(issue_order=idx)
            messages.success(request, 'Article order updated.')

        elif action == 'add_section':
            Section.objects.create(
                issue=issue,
                name=request.POST.get('section_name', 'New Section'),
                order=issue.sections.count(),
            )
            messages.success(request, 'Section added.')

        elif action == 'delete_section':
            section_pk = request.POST.get('section_pk')
            if section_pk:
                Section.objects.filter(pk=section_pk, issue=issue).delete()
                messages.success(request, 'Section deleted.')

        elif action == 'assign_section':
            submission_pk = request.POST.get('submission_pk')
            section_pk = request.POST.get('section_pk')
            if submission_pk:
                sub = get_object_or_404(Submission, pk=submission_pk, issue=issue)
                if section_pk:
                    section = get_object_or_404(Section, pk=section_pk, issue=issue)
                    sub.section = section
                else:
                    sub.section = None
                sub.save(update_fields=['section'])
                messages.success(request, 'Section assigned.')

        elif action == 'publish':
            from django.utils import timezone
            issue.is_published = True
            issue.published_at = timezone.now().date()
            issue.save()
            messages.success(request, f'Issue #{issue.number} published!')

        elif action == 'unpublish':
            issue.is_published = False
            issue.published_at = None
            issue.save()
            messages.success(request, 'Issue unpublished.')

        return redirect('journal_admin_issue_edit', pk=issue.pk)

    # GET: gather data for the template
    assigned_articles = issue.submissions.order_by('issue_order').select_related('author')
    available_articles = Submission.objects.filter(
        Q(status=SubmissionStatus.ACCEPTED) | Q(status=SubmissionStatus.IN_PRODUCTION),
        issue__isnull=True,
    ).select_related('author')
    sections = issue.sections.all()

    return render(request, 'journal_admin/issue_edit.html', {
        'issue': issue,
        'assigned_articles': assigned_articles,
        'available_articles': available_articles,
        'sections': sections,
    })


# ── Articles List & Detail ───────────────────────────────────────

@journal_admin_required
def article_list(request):
    from apps.submissions.models import Submission, SubmissionStatus
    from apps.journal.models import Issue

    qs = Submission.objects.select_related('author', 'issue').order_by('-submission_date', '-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    issue_filter = request.GET.get('issue', '')
    year_filter = request.GET.get('year', '')
    q = request.GET.get('q', '').strip()
    reviewer_q = request.GET.get('reviewer', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if issue_filter:
        qs = qs.filter(issue__pk=issue_filter)
    if year_filter:
        qs = qs.filter(issue__year=year_filter)
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(author__first_name__icontains=q) |
            Q(author__last_name__icontains=q) |
            Q(author__email__icontains=q)
        ).distinct()
    if reviewer_q:
        from apps.reviewers.models import ReviewerInvitation
        inv_sub_pks = ReviewerInvitation.objects.filter(
            Q(reviewer__first_name__icontains=reviewer_q) |
            Q(reviewer__last_name__icontains=reviewer_q) |
            Q(reviewer__email__icontains=reviewer_q)
        ).values_list('submission_id', flat=True)
        qs = qs.filter(pk__in=inv_sub_pks)

    issues = Issue.objects.order_by('-year', '-number')
    years = Issue.objects.values_list('year', flat=True).distinct().order_by('-year')

    return render(request, 'journal_admin/article_list.html', {
        'submissions': qs,
        'statuses': SubmissionStatus.choices,
        'issues': issues,
        'years': years,
        'status_filter': status_filter,
        'issue_filter': issue_filter,
        'year_filter': year_filter,
        'q': q,
        'reviewer_q': reviewer_q,
    })


@journal_admin_required
def article_detail_admin(request, pk):
    from apps.submissions.models import Submission
    from apps.notifications.models import AuditEvent
    from apps.reviewers.models import ReviewerInvitation
    from apps.reviews.models import Review
    from apps.editorial.models import EditorialDecision, EditorialAssignment

    submission = get_object_or_404(Submission, pk=pk)
    revisions = submission.revisions.prefetch_related('assets').order_by('-version')
    decisions = EditorialDecision.objects.filter(submission=submission).order_by('round')
    assignments = EditorialAssignment.objects.filter(submission=submission).select_related('editor').order_by('-assigned_at')
    invitations = ReviewerInvitation.objects.filter(submission=submission).select_related('reviewer').order_by('-sent_at')
    reviews = Review.objects.filter(invitation__submission=submission).select_related('invitation__reviewer').order_by('-submitted_at')
    audit_events = AuditEvent.objects.filter(submission=submission).select_related('actor').order_by('-timestamp')

    # Production build if any
    build = None
    canonical_doc = None
    current_rev = submission.get_current_revision()
    if current_rev:
        try:
            canonical_doc = current_rev.canonical_document
            build = getattr(canonical_doc, 'html_build', None)
        except Exception:
            pass

    return render(request, 'journal_admin/article_detail.html', {
        'submission': submission,
        'revisions': revisions,
        'decisions': decisions,
        'assignments': assignments,
        'invitations': invitations,
        'reviews': reviews,
        'audit_events': audit_events,
        'canonical_doc': canonical_doc,
        'build': build,
        'current_rev': current_rev,
    })
