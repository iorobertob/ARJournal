from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('submissions', views.SubmissionViewSet, basename='api-submission')

urlpatterns = [
    path('', include(router.urls)),
    path('editor/reviewer-suggestions/<int:submission_id>/', views.ReviewerSuggestionsView.as_view()),
    path('editor/reviewer-invitations/', views.ReviewerInvitationView.as_view()),
    path('editor/decisions/', views.EditorialDecisionView.as_view()),
    path('reviews/<int:review_id>/', views.ReviewDetailView.as_view()),
    path('reviews/<int:review_id>/annotations/', views.ReviewAnnotationView.as_view()),
    path('documents/<int:document_id>/exports/pdf/', views.PDFExportView.as_view()),
    path('public/articles/<int:document_id>/', views.PublicArticleView.as_view()),
    path('public/issues/', views.PublicIssueListView.as_view()),
]
