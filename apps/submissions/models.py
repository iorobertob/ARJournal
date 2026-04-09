import uuid
from django.db import models
from django.conf import settings
from apps.journal.models import ArticleType, Issue, Section


class SubmissionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED = 'submitted', 'Submitted – Awaiting Technical Check'
    TECHNICAL_CHECK = 'technical_check', 'Technical Check'
    DESK_REVIEW = 'desk_review', 'Desk Review'
    REVIEWER_SUGGESTION = 'reviewer_suggestion', 'Reviewer Suggestion'
    UNDER_REVIEW = 'under_review', 'Under Review'
    REVISION_REQUESTED = 'revision_requested', 'Revision Requested'
    REVISED = 'revised', 'Revised'
    ACCEPTED = 'accepted', 'Accepted'
    IN_PRODUCTION = 'in_production', 'In Production'
    PUBLISHED = 'published', 'Published'
    REJECTED = 'rejected', 'Rejected'
    DESK_REJECTED = 'desk_rejected', 'Desk Rejected'


class Submission(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submissions',
    )
    corresponding_author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='corresponding_submissions',
    )
    issue = models.ForeignKey(Issue, on_delete=models.SET_NULL, null=True, blank=True, related_name='submissions')
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True)
    issue_order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=1000)
    subtitle = models.CharField(max_length=500, blank=True, default='')
    article_type = models.CharField(max_length=50, choices=ArticleType.choices, default=ArticleType.RESEARCH_ARTICLE)
    abstract = models.TextField(blank=True, default='')
    keywords = models.JSONField(default=list, blank=True)
    disciplines = models.JSONField(default=list, blank=True)
    artistic_mediums = models.JSONField(default=list, blank=True)
    language = models.CharField(max_length=10, default='en')
    status = models.CharField(max_length=30, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT)
    cover_letter = models.TextField(blank=True, default='')
    funding_statement = models.TextField(blank=True, default='')
    conflict_of_interest = models.TextField(blank=True, default='None declared.')
    ethics_declaration = models.JSONField(default=dict, blank=True)
    ai_use_statement = models.TextField(blank=True, default='')
    license_preference = models.CharField(max_length=50, default='CC-BY')
    originality_confirmed = models.BooleanField(default=False)
    submission_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title[:60]} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        if not self.slug:
            import re, uuid as _uuid
            base = re.sub(r'[^a-z0-9]+', '-', self.title.lower())[:60].strip('-')
            self.slug = f'{base}-{str(_uuid.uuid4())[:8]}'
        super().save(*args, **kwargs)

    def get_current_revision(self):
        return self.revisions.order_by('-version').first()


class RevisionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED = 'submitted', 'Submitted'
    UNDER_REVIEW = 'under_review', 'Under Review'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'


class SubmissionRevision(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='revisions')
    version = models.PositiveIntegerField(default=1)
    manuscript_file = models.FileField(upload_to='manuscripts/')
    status = models.CharField(max_length=20, choices=RevisionStatus.choices, default=RevisionStatus.DRAFT)
    notes = models.TextField(blank=True, default='')
    response_letter = models.FileField(upload_to='response_letters/', blank=True, null=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        unique_together = ('submission', 'version')

    def __str__(self):
        return f'{self.submission.title[:40]} — v{self.version}'


class AssetKind(models.TextChoices):
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'
    AUDIO = 'audio', 'Audio'
    DATA = 'data', 'Dataset / Appendix'
    SUPPLEMENTARY = 'supplementary', 'Supplementary File'
    TRANSCRIPT = 'transcript', 'Transcript'
    POSTER = 'poster', 'Video Poster Image'


class SubmissionAsset(models.Model):
    revision = models.ForeignKey(SubmissionRevision, on_delete=models.CASCADE, related_name='assets')
    kind = models.CharField(max_length=20, choices=AssetKind.choices)
    file = models.FileField(upload_to='assets/')
    original_filename = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True)
    caption = models.TextField(blank=True, default='')
    alt_text = models.CharField(max_length=500, blank=True, default='')
    rights_cleared = models.BooleanField(default=False)
    rights_notes = models.TextField(blank=True, default='')
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.get_kind_display()}: {self.original_filename}'


class SimilarityCheck(models.Model):
    """Turnitin / similarity check result for a submission revision."""
    revision = models.OneToOneField(SubmissionRevision, on_delete=models.CASCADE, related_name='similarity_check')
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('processing', 'Processing'), ('complete', 'Complete'), ('error', 'Error')],
        default='pending',
    )
    similarity_score = models.FloatField(null=True, blank=True)
    report_url = models.URLField(blank=True, default='')
    provider_submission_id = models.CharField(max_length=255, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Check for {self.revision} — {self.status}'
