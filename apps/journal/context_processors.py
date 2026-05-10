from .models import JournalConfig, Issue


def journal_config(request):
    current_issue = Issue.objects.filter(is_current=True).first()
    unread_notifications_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        from apps.notifications.models import Notification
        qs = Notification.objects.filter(user=request.user).order_by('-created_at')
        unread_notifications_count = qs.filter(read=False).count()
        recent_notifications = list(qs[:6])
    return {
        'journal': JournalConfig.get(),
        'current_issue': current_issue,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }
