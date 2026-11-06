from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='governance_home'),
    path('report.csv', views.report_csv, name='governance_report_csv'),
    path('report.pdf', views.report_pdf, name='governance_report_pdf'),

    path('submissions/', views.submission_list, name='governance_submissions'),

    path('calls/', views.call_list, name='governance_calls'),
    path('calls/new/', views.call_edit, name='governance_call_create'),
    path('calls/<int:pk>/edit/', views.call_edit, name='governance_call_edit'),
    path('calls/<int:pk>/delete/', views.call_delete, name='governance_call_delete'),

    path('meetings/', views.meeting_list, name='governance_meetings'),
    path('meetings/new/', views.meeting_edit, name='governance_meeting_create'),
    path('meetings/<int:pk>/edit/', views.meeting_edit, name='governance_meeting_edit'),
    path('meetings/<int:pk>/delete/', views.meeting_delete, name='governance_meeting_delete'),

    path('timeline/', views.timeline, name='governance_timeline'),

    path('access/', views.access, name='governance_access'),
]
