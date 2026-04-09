from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import UserProfile


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'author/profile.html', {'profile': profile})


@login_required
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
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
            profile.photo = request.FILES['photo']
        profile.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'author/profile_edit.html', {'profile': profile})
