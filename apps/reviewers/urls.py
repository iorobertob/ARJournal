from django.urls import path
from . import views

urlpatterns = [
    path('suggest/<int:submission_pk>/', views.generate_suggestions, name='generate_suggestions'),
    path('suggest/<int:submission_pk>/search/', views.reviewer_search_json, name='reviewer_search_json'),
    path('suggest/<int:submission_pk>/add/', views.add_suggestion, name='add_suggestion'),
    path('approve/<int:suggestion_pk>/', views.approve_reviewer, name='approve_reviewer'),
    path('remove/<int:suggestion_pk>/', views.remove_suggestion, name='remove_suggestion'),
    path('invite/<int:submission_pk>/', views.send_invitations, name='send_invitations'),
    path('invitation/<uuid:token>/', views.invitation_response, name='invitation_response'),
]
