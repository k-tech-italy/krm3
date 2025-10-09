from django.urls import include, path

from .views import HomeView, AvailabilityReportView, ReportView, TaskReportView, ReleasesView

urlpatterns = [
    path('', HomeView.as_view()),
    path('home/', HomeView.as_view(), name='home'),
    path('availability/', AvailabilityReportView.as_view(), name='availability'),
    path('report/', ReportView.as_view(), name='report'),
    path('report/<str:month>/', ReportView.as_view(), name='report-month'),
    path('report/export/<str:month>/', ReportView.as_view(), {'export': True}, name='export_report'),
    path('task_report/', TaskReportView.as_view(), name='task_report'),
    path('releases/', ReleasesView.as_view(), name='releases'),
    path('missions/', include('krm3.missions.urls')),
]
