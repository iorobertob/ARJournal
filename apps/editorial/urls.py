from django.urls import path
from . import views

urlpatterns = [
    path('', views.editorial_dashboard, name='editorial_dashboard'),
    path('submission/<int:pk>/', views.submission_detail, name='editorial_submission'),
    path('submission/<int:pk>/screen/', views.record_screening, name='editorial_screen'),
    path('submission/<int:pk>/decide/', views.record_decision, name='editorial_decide'),
]
