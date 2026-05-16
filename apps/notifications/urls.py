from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notifications'),
    path('mark-read/', views.mark_all_read, name='mark_notifications_read'),
    path('<int:pk>/read/', views.mark_one_read, name='mark_notification_read'),
    path('t/<uuid:token>/', views.track_open, name='email_track_open'),
]
