from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.dashboard, name='journal_admin_dashboard'),
    path('users/', admin_views.user_list, name='journal_admin_users'),
    path('users/<int:pk>/edit/', admin_views.user_edit, name='journal_admin_user_edit'),
    path('settings/', admin_views.journal_settings, name='journal_admin_settings'),
]
