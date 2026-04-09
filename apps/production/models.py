import uuid
from django.db import models
from apps.documents.models import CanonicalDocument


class HTMLBuild(models.Model):
    """A published HTML rendering of a canonical document."""
    document = models.OneToOneField(CanonicalDocument, on_delete=models.CASCADE, related_name='html_build')
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    built_at = models.DateTimeField(auto_now=True)
    build_hash = models.CharField(max_length=64, blank=True)
    html_content = models.TextField(blank=True, default='')
    table_of_contents = models.JSONField(default=list, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    access_mode = models.CharField(
        max_length=20,
        choices=[('open', 'Open'), ('registered', 'Registered Users'), ('embargoed', 'Embargoed')],
        default='open',
    )

    def __str__(self):
        return f'HTMLBuild: {self.slug}'

    def save(self, *args, **kwargs):
        if not self.slug:
            submission = self.document.revision.submission
            self.slug = submission.slug
        super().save(*args, **kwargs)


class PDFExport(models.Model):
    document = models.ForeignKey(CanonicalDocument, on_delete=models.CASCADE, related_name='pdf_exports')
    mode = models.CharField(max_length=20, choices=[('flat', 'Flat'), ('interactive', 'Interactive')], default='flat')
    file = models.FileField(upload_to='pdf_exports/', blank=True, null=True)
    download_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    expires_at = models.DateTimeField()
    downloaded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'PDF {self.mode} — {self.document}'


class DOIDeposit(models.Model):
    document = models.OneToOneField(CanonicalDocument, on_delete=models.CASCADE, related_name='doi_deposit')
    doi = models.CharField(max_length=200, blank=True)
    deposited_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('deposited', 'Deposited'), ('registered', 'Registered'), ('failed', 'Failed')],
        default='pending',
    )
    crossref_response = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f'DOI: {self.doi or "pending"} — {self.document}'
