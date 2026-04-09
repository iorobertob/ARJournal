from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('issues/<int:number>/', views.issue_detail, name='issue_detail'),
    path('articles/<slug:slug>/', views.article_detail, name='article_detail'),
    path('archive/', views.archive, name='archive'),
    path('about/', views.about, name='about'),
    path('submit/', views.submit_info, name='submit_info'),
    path('authors/<int:pk>/', views.author_page, name='author_page'),
    path('download/template/', views.download_template, name='download_template'),
]
