from rest_framework import routers

from krm3.timesheet.api import views as api_views

router = routers.SimpleRouter()

router.register('task', api_views.TaskAPIViewSet, basename='api-task')

urlpatterns = router.urls
