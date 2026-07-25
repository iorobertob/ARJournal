from django.urls import path
from . import views

urlpatterns = [
    path('', views.editorial_dashboard, name='editorial_dashboard'),
    path('review-model/', views.set_review_model, name='set_review_model'),
    path('submission/<int:pk>/', views.submission_detail, name='editorial_submission'),
    path('submission/<int:pk>/preview/', views.article_preview, name='editorial_article_preview'),
    path('submission/<int:pk>/screen/', views.record_screening, name='editorial_screen'),
    path('submission/<int:pk>/decide/', views.record_decision, name='editorial_decide'),
    path('submission/<int:submission_pk>/assign/', views.assign_editor, name='assign_editor'),
    path('submission/<int:submission_pk>/assignment/<int:assignment_pk>/remove/', views.remove_editor, name='remove_editor'),
    path('submission/<int:submission_pk>/editors/search/', views.editor_search_json, name='editor_search_json'),
    path('submission/<int:pk>/reinvite/<int:reviewer_pk>/', views.reinvite_reviewer, name='reinvite_reviewer'),
]
