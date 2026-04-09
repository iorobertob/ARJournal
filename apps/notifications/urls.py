from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notifications'),
    path('mark-read/', views.mark_all_read, name='mark_notifications_read'),
]
