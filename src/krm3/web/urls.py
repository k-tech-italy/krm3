from django.urls import include, path

from .views import HomeView, AvailabilityReportView, ReportView, TaskReportView

urlpatterns = [
    path('', HomeView.as_view()),
    path('home/', HomeView.as_view(), name='home'),
    path('availability/', AvailabilityReportView.as_view(), name='availability'),
    path('report/', ReportView.as_view(), name='report'),
    path('task_report/', TaskReportView.as_view(), name='task_report'),
    path('missions/', include('krm3.missions.urls'))
]
