from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.dashboard, name='journal_admin_dashboard'),
    path('users/', admin_views.user_list, name='journal_admin_users'),
    path('users/<int:pk>/edit/', admin_views.user_edit, name='journal_admin_user_edit'),
    path('settings/', admin_views.journal_settings, name='journal_admin_settings'),
    # Issue & Volume assembly
    path('issues/', admin_views.issue_list, name='journal_admin_issues'),
    path('issues/new/', admin_views.issue_create, name='journal_admin_issue_create'),
    path('issues/<int:pk>/', admin_views.issue_edit, name='journal_admin_issue_edit'),
    # Articles
    path('articles/', admin_views.article_list, name='journal_admin_articles'),
    path('articles/<int:pk>/', admin_views.article_detail_admin, name='journal_admin_article'),
]
