from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('settings/', views.account_settings, name='account_settings'),
    path('delete/', views.delete_account, name='delete_account'),
]
