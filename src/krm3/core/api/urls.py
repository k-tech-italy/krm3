from rest_framework.routers import SimpleRouter

from .views import (BlacklistRefreshAPIViewSet, CityAPIViewSet, ClientAPIViewSet,
                    CountryAPIViewSet, ProjectAPIViewSet, ResourceAPIViewSet, UserAPIViewSet,
                    TimesheetModelAPIViewSet, )

router = SimpleRouter()
router.register('blacklist', BlacklistRefreshAPIViewSet, basename='api-refreshtoken')
router.register('resource', ResourceAPIViewSet, basename='api-resources')
router.register('city', CityAPIViewSet, basename='api-city')
router.register('country', CountryAPIViewSet, basename='api-country')
router.register('project', ProjectAPIViewSet, basename='api-project')
router.register('client', ClientAPIViewSet, basename='api-client')
router.register('user', UserAPIViewSet, basename='user')
router.register('timesheet', TimesheetModelAPIViewSet, basename='api-timesheet-model')

urlpatterns = []

urlpatterns += router.urls
