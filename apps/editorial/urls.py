from django.urls import path
from . import views

urlpatterns = [
    path('', views.editorial_dashboard, name='editorial_dashboard'),
    path('submission/<int:pk>/', views.submission_detail, name='editorial_submission'),
    path('submission/<int:pk>/screen/', views.record_screening, name='editorial_screen'),
    path('submission/<int:pk>/decide/', views.record_decision, name='editorial_decide'),
    path('submission/<int:submission_pk>/assign/', views.assign_editor, name='assign_editor'),
    path('submission/<int:submission_pk>/editors/search/', views.editor_search_json, name='editor_search_json'),
]
