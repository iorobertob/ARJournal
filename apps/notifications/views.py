from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notification_list(request):
    if request.method == 'POST' and request.POST.get('action') == 'mark_read':
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications')

    qs = Notification.objects.filter(user=request.user)
    unread_count = qs.filter(read=False).count()
    notifications = list(qs[:100])
    return render(request, 'notifications/list.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({'status': 'ok'})


@login_required
@require_POST
def mark_one_read(request, pk):
    Notification.objects.filter(user=request.user, pk=pk).update(read=True)
    return JsonResponse({'status': 'ok'})
