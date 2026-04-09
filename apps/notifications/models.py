from django.db import models
from django.conf import settings
from apps.submissions.models import Submission


class NotificationType(models.TextChoices):
    SUBMISSION_RECEIVED = 'submission_received', 'Submission Received'
    CORRECTIONS_REQUESTED = 'corrections_requested', 'Corrections Requested'
    REVIEWER_INVITED = 'reviewer_invited', 'Reviewer Invited'
    REVIEW_SUBMITTED = 'review_submitted', 'Review Submitted'
    REVIEW_OVERDUE = 'review_overdue', 'Review Overdue'
    DECISION_SENT = 'decision_sent', 'Decision Sent'
    PROOF_READY = 'proof_ready', 'Proof Ready'
    PUBLISHED = 'published', 'Article Published'
    GENERAL = 'general', 'General'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices, default=NotificationType.GENERAL)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True, default='')
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.notification_type}'


class EmailLog(models.Model):
    to_email = models.EmailField()
    subject = models.CharField(max_length=500)
    template_name = models.CharField(max_length=100, blank=True)
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')],
        default='pending',
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, default='')

    def __str__(self):
        return f'{self.to_email} — {self.subject[:50]} ({self.status})'


class AuditEvent(models.Model):
    """Immutable audit trail for all significant workflow events."""
    submission = models.ForeignKey(
        Submission, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_events',
    )
    event_type = models.CharField(max_length=100)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
    )
    payload = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.event_type} @ {self.timestamp}'
