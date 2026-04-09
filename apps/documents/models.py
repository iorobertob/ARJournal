import uuid
from django.db import models
from apps.submissions.models import SubmissionRevision


class CanonicalDocument(models.Model):
    """The canonical JSON representation of a manuscript revision."""
    revision = models.OneToOneField(SubmissionRevision, on_delete=models.CASCADE, related_name='canonical_document')
    schema_version = models.CharField(max_length=10, default='1.0')
    data = models.JSONField(default=dict)
    parse_warnings = models.JSONField(default=list, blank=True)
    parse_errors = models.JSONField(default=list, blank=True)
    html_build_ok = models.BooleanField(default=False)
    pdf_build_ok = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Doc: {self.revision}'

    @property
    def blind_data(self):
        """Return data with author info stripped for double-blind."""
        import copy
        d = copy.deepcopy(self.data)
        if 'contributors' in d:
            for c in d['contributors']:
                c['displayName'] = 'Author'
                c['email'] = ''
                c['orcid'] = ''
                c['institution'] = ''
                c['department'] = ''
        return d


class DocumentAsset(models.Model):
    document = models.ForeignKey(CanonicalDocument, on_delete=models.CASCADE, related_name='doc_assets')
    asset_id = models.CharField(max_length=100)
    kind = models.CharField(max_length=20)
    submission_asset = models.ForeignKey(
        'submissions.SubmissionAsset', on_delete=models.SET_NULL, null=True, blank=True
    )
    mime_type = models.CharField(max_length=100, blank=True)
    rights = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f'{self.asset_id} ({self.kind})'
