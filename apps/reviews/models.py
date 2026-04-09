from django.db import models
from django.conf import settings
from apps.reviewers.models import ReviewerInvitation


class ReviewStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED = 'submitted', 'Submitted'
    MODERATION_REQUIRED = 'moderation_required', 'Moderation Required'
    MODERATED = 'moderated', 'Moderated'
    RELEASED = 'released', 'Released to Author'


class Recommendation(models.TextChoices):
    ACCEPT = 'accept', 'Accept'
    MINOR_REVISION = 'minor_revision', 'Minor Revision'
    MAJOR_REVISION = 'major_revision', 'Major Revision'
    REJECT = 'reject', 'Reject'


class Review(models.Model):
    invitation = models.OneToOneField(ReviewerInvitation, on_delete=models.CASCADE, related_name='review')
    status = models.CharField(max_length=30, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    recommendation = models.CharField(max_length=20, choices=Recommendation.choices, blank=True)
    scores = models.JSONField(default=dict, blank=True)
    expertise_self_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    summary = models.TextField(blank=True, default='')
    strengths = models.TextField(blank=True, default='')
    major_issues = models.TextField(blank=True, default='')
    minor_issues = models.TextField(blank=True, default='')
    ethical_concerns = models.TextField(blank=True, default='')
    comments_to_author = models.TextField(blank=True, default='')
    comments_to_editor = models.TextField(blank=True, default='')
    conflict_confirmed = models.BooleanField(default=False)
    draft_saved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review by {self.invitation.reviewer.display_name} — {self.invitation.submission}'

    @property
    def reviewer(self):
        return self.invitation.reviewer

    @property
    def submission(self):
        return self.invitation.submission


class ReviewAnnotation(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='annotations')
    anchor_id = models.CharField(max_length=100, blank=True)
    block_id = models.CharField(max_length=100)
    comment = models.TextField()
    selector_data = models.JSONField(default=dict, blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Annotation on {self.block_id} by {self.review.reviewer.display_name}'


class ModerationStatus(models.TextChoices):
    SUBMITTED = 'submitted', 'Submitted'
    IN_MODERATION = 'in_moderation', 'In Moderation'
    MODERATED = 'moderated', 'Moderated'
    RELEASED = 'released', 'Released to Author'


class ReviewModeration(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name='moderation')
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='review_moderations',
    )
    original_comments_to_author = models.TextField(blank=True, default='')
    moderated_comments_to_author = models.TextField(blank=True, default='')
    moderation_notes = models.TextField(blank=True, default='')
    conflict_flagged = models.BooleanField(default=False)
    conflict_note = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=ModerationStatus.choices, default=ModerationStatus.SUBMITTED)
    moderated_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Moderation of {self.review}'
