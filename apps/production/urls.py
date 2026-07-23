from django.urls import path
from . import views

urlpatterns = [
    path('build/<int:document_pk>/', views.build_html, name='build_html'),
    path('publish/<int:document_pk>/', views.publish_article, name='publish_article'),
    path('unpublish/<int:document_pk>/', views.unpublish_article, name='unpublish_article'),
    path('pdf/request/<int:document_pk>/', views.request_pdf, name='request_pdf'),
    path('pdf/download/<uuid:token>/', views.download_pdf, name='download_pdf'),
    path('admin/preview/<int:document_pk>/', views.admin_preview, name='admin_preview'),
    path('admin/pdf/<int:document_pk>/', views.admin_request_pdf, name='admin_request_pdf'),
    path('slug/<int:document_pk>/', views.update_slug, name='update_article_slug'),
    path('ingest/<int:submission_pk>/', views.trigger_ingest, name='trigger_ingest'),
    path('stream/<path:media_path>', views.stream_media, name='stream_media'),
]
