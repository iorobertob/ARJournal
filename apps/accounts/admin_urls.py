from django.urls import path
from . import admin_views

urlpatterns = [
    path('', admin_views.dashboard, name='journal_admin_dashboard'),
    path('users/', admin_views.user_list, name='journal_admin_users'),
    path('users/<int:pk>/edit/', admin_views.user_edit, name='journal_admin_user_edit'),
    path('users/<int:pk>/delete/', admin_views.user_delete, name='journal_admin_user_delete'),
    path('settings/', admin_views.journal_settings, name='journal_admin_settings'),
    path('homepage/', admin_views.homepage_settings, name='journal_admin_homepage'),
    # Issue & Volume assembly
    path('issues/', admin_views.issue_list, name='journal_admin_issues'),
    path('issues/new/', admin_views.issue_create, name='journal_admin_issue_create'),
    path('issues/<int:pk>/', admin_views.issue_edit, name='journal_admin_issue_edit'),
    # Articles
    path('articles/', admin_views.article_list, name='journal_admin_articles'),
    path('articles/<int:pk>/', admin_views.article_detail_admin, name='journal_admin_article'),
    # Email log
    path('email-log/', admin_views.email_log, name='journal_admin_email_log'),
    path('email-log/<int:pk>/preview/', admin_views.email_log_preview, name='journal_admin_email_log_preview'),
    # News / blog posts
    path('news/', admin_views.news_list, name='journal_admin_news'),
    path('news/new/', admin_views.news_edit, name='journal_admin_news_create'),
    path('news/<int:pk>/edit/', admin_views.news_edit, name='journal_admin_news_edit'),
    path('news/<int:pk>/delete/', admin_views.news_delete, name='journal_admin_news_delete'),
]
