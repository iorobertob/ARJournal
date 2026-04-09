from django.urls import path
from . import views

urlpatterns = [
    path('suggest/<int:submission_pk>/', views.generate_suggestions, name='generate_suggestions'),
    path('approve/<int:suggestion_pk>/', views.approve_reviewer, name='approve_reviewer'),
    path('invite/<int:submission_pk>/', views.send_invitations, name='send_invitations'),
    path('invitation/<uuid:token>/', views.invitation_response, name='invitation_response'),
]
