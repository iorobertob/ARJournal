from django.urls import path
from . import views

urlpatterns = [
    path('build/<int:document_pk>/', views.build_html, name='build_html'),
    path('publish/<int:document_pk>/', views.publish_article, name='publish_article'),
    path('pdf/request/<int:document_pk>/', views.request_pdf, name='request_pdf'),
    path('pdf/download/<uuid:token>/', views.download_pdf, name='download_pdf'),
]
