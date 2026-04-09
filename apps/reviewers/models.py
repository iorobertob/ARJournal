import uuid
from django.db import models
from django.conf import settings
from apps.submissions.models import Submission


class ReviewerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviewer_profile',
    )
    expertise_keywords = models.JSONField(default=list, blank=True)
    disciplines = models.JSONField(default=list, blank=True)
    sub_disciplines = models.JSONField(default=list, blank=True)
    methodologies = models.JSONField(default=list, blank=True)
    artistic_mediums = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    conflicts = models.JSONField(default=list, blank=True)
    unavailable_dates = models.JSONField(default=list, blank=True)
    preferred_review_models = models.JSONField(default=list, blank=True)
    expertise_statement = models.TextField(blank=True, default='')
    avg_turnaround_days = models.FloatField(default=21.0)
    responsiveness_score = models.FloatField(default=0.7)
    quality_score = models.FloatField(default=0.7)
    active_invitations_count = models.PositiveIntegerField(default=0)
    total_reviews_completed = models.PositiveIntegerField(default=0)
    last_invited_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Reviewer: {self.user.email}'


class SuggestionStatus(models.TextChoices):
    SUGGESTED = 'suggested', 'Suggested'
    APPROVED = 'approved', 'Approved by Editor'
    REJECTED = 'rejected', 'Rejected by Editor'
    INVITED = 'invited', 'Invitation Sent'


class ReviewerSuggestion(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='reviewer_suggestions')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviewer_suggestions',
    )
    score = models.FloatField(default=0.0)
    breakdown = models.JSONField(default=dict, blank=True)
    rationale = models.TextField(blank=True, default='')
    is_primary = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=SuggestionStatus.choices, default=SuggestionStatus.SUGGESTED)
    suggested_by_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewer_suggestions_made',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-score']

    def __str__(self):
        return f'Suggestion: {self.reviewer.display_name} for {self.submission}'


class InvitationStatus(models.TextChoices):
    PENDING = 'pending', 'Pending Response'
    ACCEPTED = 'accepted', 'Accepted'
    DECLINED = 'declined', 'Declined'
    EXPIRED = 'expired', 'Expired'


class ReviewerInvitation(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='reviewer_invitations')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviewer_invitations',
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)
    magic_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    decline_reason = models.TextField(blank=True, default='')

    def __str__(self):
        return f'Invitation: {self.reviewer.display_name} — {self.submission} ({self.status})'
