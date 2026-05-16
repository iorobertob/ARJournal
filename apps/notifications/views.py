from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .models import Notification


# 1×1 transparent GIF — used as the email open-tracking pixel
_PIXEL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
    b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00'
    b'\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02'
    b'\x44\x01\x00\x3b'
)


@never_cache
def track_open(request, token):
    """Record email open via tracking pixel. No auth required (email client fires this)."""
    from .models import EmailLog
    try:
        log = EmailLog.objects.get(tracking_token=token)
        log.opened_count += 1
        if log.opened_at is None:
            log.opened_at = timezone.now()
        log.save(update_fields=['opened_count', 'opened_at'])
    except EmailLog.DoesNotExist:
        pass
    return HttpResponse(_PIXEL_GIF, content_type='image/gif')


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
