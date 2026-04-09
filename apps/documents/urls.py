from django.urls import path
from . import views

urlpatterns = [
    path('<int:pk>/json/', views.canonical_document_json, name='document_json'),
]
