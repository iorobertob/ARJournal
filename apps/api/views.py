from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import (
    SubmissionSerializer, SubmissionAssetSerializer,
    ReviewerSuggestionSerializer, ReviewSerializer,
    ReviewAnnotationSerializer, EditorialDecisionSerializer,
    PublicArticleSerializer, PDFExportRequestSerializer,
)
from apps.submissions.models import Submission, SubmissionRevision, SubmissionAsset
from apps.reviewers.models import ReviewerSuggestion, ReviewerInvitation
from apps.reviews.models import Review, ReviewAnnotation
from apps.editorial.models import EditorialDecision
from apps.documents.models import CanonicalDocument
from apps.production.models import HTMLBuild, PDFExport


class IsEditorial(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_editorial_access()


# ── Submissions ───────────────────────────────────────────────────────────────

class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.has_editorial_access():
            return Submission.objects.all()
        return Submission.objects.filter(author=user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], url_path='assets')
    def upload_asset(self, request, pk=None):
        submission = self.get_object()
        revision = submission.get_current_revision()
        if not revision:
            return Response({'error': 'No revision found.'}, status=400)
        serializer = SubmissionAssetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(revision=revision)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['post'], url_path='ingest')
    def ingest(self, request, pk=None):
        submission = self.get_object()
        revision = submission.get_current_revision()
        if not revision:
            return Response({'error': 'No revision.'}, status=400)
        from apps.production.tasks import ingest_submission
        ingest_submission.delay(revision.pk)
        return Response({'status': 'ingestion_queued', 'revision_id': revision.pk}, status=202)


# ── Editorial ─────────────────────────────────────────────────────────────────

class ReviewerSuggestionsView(APIView):
    permission_classes = [IsEditorial]

    def get(self, request, submission_id):
        submission = get_object_or_404(Submission, pk=submission_id)
        suggestions = ReviewerSuggestion.objects.filter(submission=submission)
        if not suggestions.exists():
            # Auto-generate on first request
            from apps.reviewers.scorer import suggest_reviewers
            result = suggest_reviewers(submission)
            for item in result['primary']:
                ReviewerSuggestion.objects.create(
                    submission=submission,
                    reviewer=item['reviewer'],
                    score=item['score'],
                    breakdown=item['breakdown'],
                    rationale=item['rationale'],
                    is_primary=True,
                )
            for item in result['alternates']:
                ReviewerSuggestion.objects.create(
                    submission=submission,
                    reviewer=item['reviewer'],
                    score=item['score'],
                    breakdown=item['breakdown'],
                    rationale=item['rationale'],
                    is_primary=False,
                )
            suggestions = ReviewerSuggestion.objects.filter(submission=submission)
        serializer = ReviewerSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)


class ReviewerInvitationView(APIView):
    permission_classes = [IsEditorial]

    def post(self, request):
        submission_id = request.data.get('submissionId')
        reviewer_ids = request.data.get('reviewerIds', [])
        deadline = request.data.get('deadline')
        submission = get_object_or_404(Submission, pk=submission_id)
        created = []
        for rid in reviewer_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            reviewer = get_object_or_404(User, pk=rid)
            inv, _ = ReviewerInvitation.objects.get_or_create(
                submission=submission,
                reviewer=reviewer,
                defaults={'deadline': deadline or (timezone.now().date())},
            )
            created.append(inv.pk)
        return Response({'invited': created}, status=201)


class EditorialDecisionView(APIView):
    permission_classes = [IsEditorial]

    def post(self, request):
        serializer = EditorialDecisionSerializer(data=request.data)
        if serializer.is_valid():
            decision = serializer.save(editor=request.user)
            return Response(EditorialDecisionSerializer(decision).data, status=201)
        return Response(serializer.errors, status=400)


# ── Reviews ───────────────────────────────────────────────────────────────────

class ReviewDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, review_id):
        review = get_object_or_404(Review, pk=review_id)
        return Response(ReviewSerializer(review).data)


class ReviewAnnotationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, review_id):
        review = get_object_or_404(Review, pk=review_id)
        serializer = ReviewAnnotationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(review=review)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


# ── Documents ────────────────────────────────────────────────────────────────

class PDFExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id):
        doc = get_object_or_404(CanonicalDocument, pk=document_id)
        ser = PDFExportRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from datetime import timedelta
        exp = PDFExport.objects.create(
            document=doc,
            mode=ser.validated_data['mode'],
            expires_at=timezone.now() + timedelta(minutes=ser.validated_data['ttl_minutes']),
        )
        from apps.production.tasks import generate_pdf
        generate_pdf.delay(exp.pk)
        return Response({'export_id': exp.pk, 'download_token': str(exp.download_token)}, status=202)


# ── Public ────────────────────────────────────────────────────────────────────

class PublicArticleView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, document_id):
        build = get_object_or_404(HTMLBuild, document__pk=document_id, is_published=True)
        return Response(PublicArticleSerializer(build).data)


class PublicIssueListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from apps.journal.models import Issue
        issues = Issue.objects.filter(is_published=True)
        data = [
            {'id': i.pk, 'number': i.number, 'year': i.year, 'title': i.title, 'published_at': i.published_at}
            for i in issues
        ]
        return Response(data)
