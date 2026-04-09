from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(request, 'partials/notifications.html', {'notifications': notifications})


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({'status': 'ok'})
