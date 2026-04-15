from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='author_dashboard'),
    path('submit/step1/', views.new_submission_step1, name='submission_step1'),
    path('submit/<int:pk>/step2/', views.new_submission_step2, name='submission_step2'),
    path('submit/<int:pk>/step3/<int:rev>/', views.new_submission_step3, name='submission_step3'),
    path('submit/<int:pk>/step4/<int:rev>/', views.new_submission_step4, name='submission_step4'),
    path('submission/<int:pk>/', views.submission_detail, name='submission_detail'),
    # Resubmission wizard
    path('submit/<int:pk>/revise/step1/', views.resubmit_step1, name='resubmit_step1'),
    path('submit/<int:pk>/revise/<int:rev>/step2/', views.resubmit_step2, name='resubmit_step2'),
    path('submit/<int:pk>/revise/<int:rev>/step3/', views.resubmit_step3, name='resubmit_step3'),
    # Asset management (draft revisions only)
    path('submit/<int:pk>/revision/<int:rev>/asset/<int:asset_pk>/delete/', views.delete_revision_asset, name='delete_revision_asset'),
]
