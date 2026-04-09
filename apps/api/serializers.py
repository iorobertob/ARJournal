from rest_framework import serializers
from apps.submissions.models import Submission, SubmissionRevision, SubmissionAsset
from apps.reviewers.models import ReviewerSuggestion, ReviewerInvitation
from apps.reviews.models import Review, ReviewAnnotation
from apps.editorial.models import EditorialDecision
from apps.documents.models import CanonicalDocument
from apps.production.models import HTMLBuild, PDFExport


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['id', 'title', 'subtitle', 'article_type', 'abstract', 'keywords',
                  'disciplines', 'status', 'submission_date', 'slug']
        read_only_fields = ['status', 'submission_date', 'slug']


class SubmissionAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmissionAsset
        fields = ['id', 'kind', 'original_filename', 'mime_type', 'caption', 'alt_text', 'rights_cleared']


class ReviewerSuggestionSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.display_name', read_only=True)
    reviewer_email = serializers.CharField(source='reviewer.email', read_only=True)

    class Meta:
        model = ReviewerSuggestion
        fields = ['id', 'reviewer_name', 'reviewer_email', 'score', 'breakdown', 'rationale',
                  'is_primary', 'status']


class ReviewAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewAnnotation
        fields = ['id', 'block_id', 'anchor_id', 'comment', 'selector_data', 'resolved']


class ReviewSerializer(serializers.ModelSerializer):
    annotations = ReviewAnnotationSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'status', 'recommendation', 'scores', 'summary', 'strengths',
                  'major_issues', 'minor_issues', 'comments_to_author', 'submitted_at', 'annotations']


class EditorialDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialDecision
        fields = ['id', 'submission', 'round', 'decision_type', 'letter', 'sent_at']


class PublicArticleSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    abstract = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()

    class Meta:
        model = HTMLBuild
        fields = ['id', 'slug', 'title', 'abstract', 'authors', 'access_mode', 'published_at']

    def get_title(self, obj):
        meta = obj.document.data.get('metadata', {})
        return meta.get('title', {}).get('main', '')

    def get_abstract(self, obj):
        meta = obj.document.data.get('metadata', {})
        abstracts = meta.get('abstract', [])
        return abstracts[0].get('text', '') if abstracts else ''

    def get_authors(self, obj):
        contributors = obj.document.data.get('contributors', [])
        return [c.get('displayName', '') for c in contributors if c.get('role') == 'author']


class PDFExportRequestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['flat', 'interactive'], default='flat')
    ttl_minutes = serializers.IntegerField(default=30, min_value=5, max_value=120)
