from django.contrib import admin
from .models import Notification, EmailLog, AuditEvent


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'read', 'created_at')
    list_filter = ('notification_type', 'read')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('to_email', 'subject', 'status', 'sent_at')
    list_filter = ('status',)
    readonly_fields = ('sent_at',)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'submission', 'actor', 'timestamp')
    readonly_fields = ('timestamp', 'payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
