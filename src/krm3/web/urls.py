from django.urls import include, path

from .views import (
    HomeView,
    AvailabilityReportView,
    ReportView,
    TaskReportView,
    ReleasesView,
    SavedFilterDeleteView,
    UserProfileView,
    DocumentListView, ScanQRView,
)

urlpatterns = [
    path('', HomeView.as_view()),
    path('home/', HomeView.as_view(), name='home'),
    path('scan_qr/', ScanQRView.as_view(), name='scan-qr'),
    path('availability/', AvailabilityReportView.as_view(), name='availability'),
    path('availability/<str:month>/', AvailabilityReportView.as_view(), name='availability-report-month'),
    path('report/', ReportView.as_view(), name='report'),
    path('report/<str:month>/', ReportView.as_view(), name='report-month'),
    path('report/export/<str:month>/', ReportView.as_view(), {'export': True}, name='export_report'),
    path('task_report/', TaskReportView.as_view(), name='task_report'),
    path('task/<str:month>/', TaskReportView.as_view(), name='task-report-month'),
    path('task_report/export/<str:month>/', TaskReportView.as_view(), {'export': True}, name='export_task_report'),
    path('releases/', ReleasesView.as_view(), name='releases'),
    path('missions/', include('krm3.missions.urls')),
    path('profile/<int:pk>/', UserProfileView.as_view(), name='user_profile'),
    path('saved-filters/<int:pk>/delete/', SavedFilterDeleteView.as_view(), name='saved_filter_delete'),
    path('documents/', DocumentListView.as_view(), name='document_list'),
]
