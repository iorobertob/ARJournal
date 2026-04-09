from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='author_dashboard'),
    path('submit/step1/', views.new_submission_step1, name='submission_step1'),
    path('submit/<int:pk>/step2/', views.new_submission_step2, name='submission_step2'),
    path('submit/<int:pk>/step3/<int:rev>/', views.new_submission_step3, name='submission_step3'),
    path('submit/<int:pk>/step4/<int:rev>/', views.new_submission_step4, name='submission_step4'),
    path('submission/<int:pk>/', views.submission_detail, name='submission_detail'),
]
