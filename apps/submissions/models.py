import uuid
from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
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
    cover_image = models.ImageField(
        upload_to='covers/', blank=True, null=True,
        help_text='Cover image shown at the top of the article page (falls back to the issue cover image). '
                  'Recommended 1920×1080 (16:9), up to 2500px wide.')
    cover_caption = models.CharField(max_length=500, blank=True, default='')
    # Responsive WebP renditions of cover_image ({width: url}), generated on upload.
    cover_derivatives = models.JSONField(default=dict, blank=True)
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
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['author']),
            GinIndex(fields=['keywords'], name='submission_keywords_gin'),
        ]

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

    @property
    def cover_url(self):
        """Cover image for the article page: the uploaded cover, else the
        issue's cover image, else None."""
        if self.cover_image:
            return self.cover_image.url
        if self.issue and self.issue.cover_image:
            return self.issue.cover_image.url
        return None

    @property
    def cover_srcset(self):
        """`srcset` value for the uploaded cover's responsive derivatives, or ''.

        Only applies to the article's own uploaded cover (not the issue fallback).
        """
        if self.cover_image and self.cover_derivatives:
            return ', '.join(
                f'{url} {w}w' for w, url in sorted(
                    self.cover_derivatives.items(), key=lambda kv: int(kv[0])
                )
            )
        return ''

    @property
    def is_returned_to_author(self):
        """True when returned from technical screening and no rejection has followed."""
        if self.status != SubmissionStatus.SUBMITTED:
            return False
        check = self.screening_checks.filter(result='return_to_author').order_by('-checked_at').first()
        if check is None:
            return False
        from apps.editorial.models import DecisionType
        _rejections = {DecisionType.REJECT, DecisionType.DESK_REJECT}
        if self.editorial_decisions.filter(decision_type__in=_rejections).exists():
            return False
        # If the author has submitted a newer revision after the screening return,
        # they have already responded — no longer awaiting correction.
        latest_rev = self.revisions.order_by('-version').first()
        if latest_rev and latest_rev.submitted_at and latest_rev.submitted_at > check.checked_at:
            return False
        return True


class RevisionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SUBMITTED = 'submitted', 'Submitted'
    UNDER_REVIEW = 'under_review', 'Under Review'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'


class RevisionSource(models.TextChoices):
    LATEX = 'latex', 'LaTeX'
    WYSIWYG = 'wysiwyg', 'WYSIWYG Editor'


class SubmissionRevision(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='revisions')
    version = models.PositiveIntegerField(default=1)
    source_type = models.CharField(max_length=16, choices=RevisionSource.choices, default=RevisionSource.LATEX)
    manuscript_file = models.FileField(upload_to='manuscripts/', blank=True, null=True)
    wysiwyg_data = models.JSONField(null=True, blank=True)
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
    # Image sizing metadata (populated for image assets on upload).
    role = models.CharField(max_length=10, blank=True, default='')  # content | hero | logo
    intrinsic_width = models.PositiveIntegerField(null=True, blank=True)
    intrinsic_height = models.PositiveIntegerField(null=True, blank=True)
    derivatives = models.JSONField(default=dict, blank=True)  # {width(str): url}
    # HLS streaming metadata (populated for video/audio assets by transcode_asset).
    HLS_NONE, HLS_PENDING, HLS_PROCESSING, HLS_READY, HLS_ERROR = (
        'none', 'pending', 'processing', 'ready', 'error')
    HLS_STATUS_CHOICES = [
        (HLS_NONE, 'Not applicable'), (HLS_PENDING, 'Pending'),
        (HLS_PROCESSING, 'Processing'), (HLS_READY, 'Ready'), (HLS_ERROR, 'Error'),
    ]
    hls_status = models.CharField(max_length=12, choices=HLS_STATUS_CHOICES, default=HLS_NONE)
    hls_master = models.CharField(max_length=500, blank=True, default='')  # MEDIA-relative path
    hls_error = models.TextField(blank=True, default='')
    duration_seconds = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.get_kind_display()}: {self.original_filename}'

    @property
    def srcset(self):
        """`srcset` string built from the image derivatives, or '' if none."""
        if not self.derivatives:
            return ''
        return ', '.join(
            f'{url} {w}w' for w, url in sorted(
                self.derivatives.items(), key=lambda kv: int(kv[0])
            )
        )


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
