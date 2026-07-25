from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('issues/<int:number>/', views.issue_detail, name='issue_detail'),
    path('articles/<slug:slug>/', views.article_detail, name='article_detail'),
    path('archive/', views.archive, name='archive'),
    path('about/', views.about, name='about'),
    path('editorial-board/', views.editorial_board, name='editorial_board'),
    path('submit/', views.submit_info, name='submit_info'),
    path('authors/<int:pk>/', views.author_page, name='author_page'),
    path('terms/', views.terms, name='terms'),
    path('policy/', views.policy, name='policy'),
    path('news/', views.news, name='news'),
    path('news/<slug:slug>/', views.news_detail, name='news_detail'),
    path('contact/', views.contact, name='contact'),
    path('partners/', views.partners, name='partners'),
    path('imprint/', views.imprint, name='imprint'),
    path('download/template/', views.download_template, name='download_template'),
]
