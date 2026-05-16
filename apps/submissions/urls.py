from django.urls import path
from . import views, wysiwyg_views

urlpatterns = [
    path('dashboard/', views.dashboard, name='author_dashboard'),
    path('submit/step1/', views.new_submission_step1, name='submission_step1'),
    path('submit/<int:pk>/metadata/', views.edit_submission_metadata, name='edit_submission_metadata'),
    path('submit/<int:pk>/step2/', views.new_submission_step2, name='submission_step2'),
    path('submit/<int:pk>/step2/editor/', wysiwyg_views.wysiwyg_editor, name='submission_step2_wysiwyg'),
    path('submit/<int:pk>/step3/<int:rev>/', views.new_submission_step3, name='submission_step3'),
    path('submit/<int:pk>/step4/<int:rev>/', views.new_submission_step4, name='submission_step4'),
    # WYSIWYG AJAX endpoints
    path('submit/<int:pk>/revision/<int:rev>/autosave/', wysiwyg_views.wysiwyg_autosave, name='wysiwyg_autosave'),
    path('submit/<int:pk>/revision/<int:rev>/upload/', wysiwyg_views.wysiwyg_asset_upload, name='wysiwyg_asset_upload'),
    path('submit/<int:pk>/bibtex/', wysiwyg_views.wysiwyg_bibtex_import, name='wysiwyg_bibtex_import'),
    path('submit/<int:pk>/metadata/save/', wysiwyg_views.wysiwyg_metadata_save, name='wysiwyg_metadata_save'),
    path('submission/<int:pk>/', views.submission_detail, name='submission_detail'),
    # Correction after screening return (single step)
    path('submit/<int:pk>/correct/', views.resubmit_after_screening, name='resubmit_after_screening'),
    # Resubmission wizard (post-review revision)
    path('submit/<int:pk>/revise/step1/', views.resubmit_step1, name='resubmit_step1'),
    path('submit/<int:pk>/revise/<int:rev>/step2/', views.resubmit_step2, name='resubmit_step2'),
    path('submit/<int:pk>/revise/<int:rev>/step3/', views.resubmit_step3, name='resubmit_step3'),
    # Asset management (draft revisions only)
    path('submit/<int:pk>/revision/<int:rev>/asset/<int:asset_pk>/delete/', views.delete_revision_asset, name='delete_revision_asset'),
    # Author self-service delete / withdrawal
    path('submission/<int:pk>/delete/', views.delete_submission, name='delete_submission'),
]
