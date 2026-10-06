from .models import JournalConfig, Issue, Partner


def journal_config(request):
    # Public pages are served by apps.journal.views; functional dashboards
    # (author/editorial/reviewer/admin) live in other apps. Use this to limit
    # public-only chrome such as the partner-logo strip.
    resolver_match = getattr(request, 'resolver_match', None)
    is_public_page = bool(
        resolver_match
        and getattr(resolver_match.func, '__module__', '').startswith('apps.journal')
    )
    current_issue = Issue.objects.filter(is_current=True, is_published=True).first()
    unread_notifications_count = 0
    recent_notifications = []
    if request.user.is_authenticated:
        from apps.notifications.models import Notification
        qs = Notification.objects.filter(user=request.user).order_by('-created_at')
        unread_notifications_count = qs.filter(read=False).count()
        recent_notifications = list(qs[:5])
    return {
        'journal': JournalConfig.get(),
        'partner_institutions': Partner.objects.filter(is_active=True),
        'is_public_page': is_public_page,
        'current_issue': current_issue,
        'unread_notifications_count': unread_notifications_count,
        'recent_notifications': recent_notifications,
    }
