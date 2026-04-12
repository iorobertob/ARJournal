from django.urls import path
from . import views

urlpatterns = [
    path('my-reviews/', views.reviewer_dashboard, name='reviewer_dashboard'),
    path('workspace/<int:invitation_pk>/', views.reviewer_workspace, name='reviewer_workspace'),
    path('<int:review_pk>/draft/', views.save_draft, name='review_save_draft'),
    path('<int:review_pk>/submit/', views.submit_review, name='review_submit'),
    path('<int:review_pk>/annotate/', views.add_annotation, name='review_annotate'),
    path('<int:review_pk>/moderate/', views.moderate_review, name='moderate_review'),
]
