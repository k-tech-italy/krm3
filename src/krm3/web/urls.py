from django.urls import include, path

from .views import (
    HomeView,
    AvailabilityReportView,
    ReportView,
    TaskReportView,
    ReleasesView,
    UserResourceView,
    DocumentListView, ScanQRView,
    ProtectedDocumentView,
    ProtectedExpenseView,
    ProtectedContractView,
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
    path('releases/', ReleasesView.as_view(), name='releases'),
    path('missions/', include('krm3.missions.urls')),
    path('resource/<int:pk>/', UserResourceView.as_view(), name='user_resource'),
    path('documents/', DocumentListView.as_view(), name='document_list'),
    path('media-auth/document/<int:pk>/', ProtectedDocumentView.as_view(), name='protected_document'),
    path('media-auth/expense/<int:pk>/', ProtectedExpenseView.as_view(), name='protected_expense'),
    path('media-auth/contract/<int:pk>/', ProtectedContractView.as_view(), name='protected_contract'),
]
