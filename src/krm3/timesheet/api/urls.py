from rest_framework import routers

from krm3.timesheet.api import views as api_views


router = routers.SimpleRouter()

router.register('', api_views.TimesheetAPIViewSet, basename='api-timesheet')

router.register('timesheet', api_views.TimesheetModelAPIViewSet, basename='api-timesheet-model')

router.register('time-entry', api_views.TimeEntryAPIViewSet, basename='api-time-entry')
router.register('special-leave-reason', api_views.SpecialLeaveReasonViewSet, basename='api-special-leave-reason')
router.register('report/export', api_views.ReportViewSet, basename='api-report')

urlpatterns = router.urls
