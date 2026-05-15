from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserProfile


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    from apps.reviewers.models import ReviewerProfile
    reviewer_profile = ReviewerProfile.objects.filter(user=request.user).first()
    return render(request, 'author/profile.html', {
        'profile': profile,
        'reviewer_profile': reviewer_profile,
    })


@login_required
def account_settings(request):
    return render(request, 'author/account_settings.html')


@login_required
def delete_account(request):
    from apps.production.models import HTMLBuild
    user = request.user
    has_published = HTMLBuild.objects.filter(
        is_published=True,
        document__revision__submission__author=user,
    ).exists()

    if request.method == 'POST':
        confirm = request.POST.get('confirm', '').strip()
        if confirm != 'DELETE':
            messages.error(request, 'Type DELETE exactly to confirm.')
            return redirect('delete_account')

        if has_published:
            from allauth.account.models import EmailAddress
            from django.contrib.auth import logout as auth_logout
            profile, _ = UserProfile.objects.get_or_create(user=user)
            user.is_active = False
            user.email = f'deleted-{user.pk}@deleted.invalid'
            user.orcid_id = ''
            user.save()
            profile.bio = ''
            profile.institution = ''
            profile.department = ''
            profile.country = ''
            profile.website = ''
            if profile.photo:
                profile.photo.delete(save=False)
                profile.photo = None
            profile.public_profile = False
            profile.save()
            EmailAddress.objects.filter(user=user).delete()
            auth_logout(request)
            return redirect('home')
        else:
            from django.contrib.auth import logout as auth_logout
            auth_logout(request)
            user.delete()
            return redirect('home')

    return render(request, 'author/delete_account.html', {
        'has_published': has_published,
    })


@login_required
def profile_edit(request):
    from apps.reviewers.models import ReviewerProfile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    reviewer_profile = ReviewerProfile.objects.filter(user=request.user).first()

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()
        profile.bio = request.POST.get('bio', profile.bio)
        profile.institution = request.POST.get('institution', profile.institution)
        profile.department = request.POST.get('department', profile.department)
        profile.country = request.POST.get('country', profile.country)
        profile.website = request.POST.get('website', profile.website)
        if request.FILES.get('photo'):
            photo = request.FILES['photo']
            if photo.size > 2 * 1024 * 1024:
                messages.error(request, 'Photo not saved — the file exceeds the 2 MB limit. Please resize the image and try again.')
            else:
                profile.photo = photo
        if user.has_editorial_access():
            profile.email_notifications = request.POST.get('email_notifications') == 'on'
        profile.save()

        if reviewer_profile:
            def _split(val):
                return [v.strip() for v in val.split(',') if v.strip()]
            reviewer_profile.expertise_statement     = request.POST.get('expertise_statement', '').strip()
            reviewer_profile.expertise_keywords      = _split(request.POST.get('expertise_keywords', ''))
            reviewer_profile.disciplines             = _split(request.POST.get('disciplines', ''))
            reviewer_profile.sub_disciplines         = _split(request.POST.get('sub_disciplines', ''))
            reviewer_profile.methodologies           = _split(request.POST.get('methodologies', ''))
            reviewer_profile.artistic_mediums        = _split(request.POST.get('artistic_mediums', ''))
            reviewer_profile.languages               = _split(request.POST.get('languages', ''))
            reviewer_profile.conflicts               = _split(request.POST.get('conflicts', ''))
            reviewer_profile.preferred_review_models = _split(request.POST.get('preferred_review_models', ''))
            reviewer_profile.save(update_fields=[
                'expertise_statement', 'expertise_keywords', 'disciplines',
                'sub_disciplines', 'methodologies', 'artistic_mediums',
                'languages', 'conflicts', 'preferred_review_models',
            ])

        messages.success(request, 'Profile updated.')
        return redirect('profile')

    return render(request, 'author/profile_edit.html', {
        'profile': profile,
        'reviewer_profile': reviewer_profile,
    })
