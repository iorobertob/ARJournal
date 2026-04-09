"""
Journal Admin views — custom platform administration (not Django admin).
Accessible to users with role journal_admin or system_admin, or is_superuser.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count

from .models import User, UserRole


def journal_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or request.user.role in (UserRole.JOURNAL_ADMIN, UserRole.SYSTEM_ADMIN)
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
        'reviewers': User.objects.filter(role=UserRole.REVIEWER).count(),
        'published': Submission.objects.filter(status=SubmissionStatus.PUBLISHED).count(),
        'issues': Issue.objects.count(),
    }
    users_by_role = (
        User.objects
        .values('role')
        .annotate(count=Count('id'))
        .order_by('role')
    )
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
        users = users.filter(role=role_filter)
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
        new_role = request.POST.get('role')
        if new_role in dict(UserRole.choices):
            user.role = new_role
            user.save(update_fields=['role'])
            messages.success(request, f'Role updated for {user.email}.')
        # Allow toggling active status
        user.is_active = bool(request.POST.get('is_active'))
        user.save(update_fields=['is_active'])
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
        journal.name = request.POST.get('name', journal.name)
        journal.tagline = request.POST.get('tagline', journal.tagline)
        journal.issn_print = request.POST.get('issn_print', journal.issn_print)
        journal.issn_online = request.POST.get('issn_online', journal.issn_online)
        journal.description = request.POST.get('description', journal.description)
        journal.contact_email = request.POST.get('contact_email', journal.contact_email)
        journal.submission_open = bool(request.POST.get('submission_open'))
        if request.FILES.get('logo'):
            journal.logo = request.FILES['logo']
        journal.save()
        messages.success(request, 'Journal settings saved.')
        return redirect('journal_admin_settings')
    return render(request, 'journal_admin/settings.html', {'journal': journal})
