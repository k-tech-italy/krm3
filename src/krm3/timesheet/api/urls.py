from rest_framework import routers

from krm3.timesheet.api import views as api_views


router = routers.SimpleRouter()

router.register('', api_views.TimesheetAPIViewSet, basename='api-timesheet')

router.register('tay-entry', api_views.DayEntryAPIViewSet, basename='api-day-entry')
router.register('task-entry', api_views.TaskEntryAPIViewSet, basename='api-task-entry')
router.register('special-leave-reason', api_views.SpecialLeaveReasonViewSet, basename='api-special-leave-reason')

urlpatterns = router.urls
