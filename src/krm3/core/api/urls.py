from rest_framework.routers import SimpleRouter

from .views import (
    CityAPIViewSet,
    ClientAPIViewSet,
    CountryAPIViewSet,
    ProjectAPIViewSet,
    ResourceAPIViewSet,
    UserAPIViewSet,
    TimesheetSubmissionAPIViewSet,
    ContactAPIViewSet,
)

router = SimpleRouter()
router.register('resource', ResourceAPIViewSet, basename='api-resources')
router.register('city', CityAPIViewSet, basename='api-city')
router.register('country', CountryAPIViewSet, basename='api-country')
router.register('project', ProjectAPIViewSet, basename='api-project')
router.register('client', ClientAPIViewSet, basename='api-client')
router.register('user', UserAPIViewSet, basename='user')
router.register('timesheet', TimesheetSubmissionAPIViewSet, basename='api-timesheet-model')
router.register(r'contacts', ContactAPIViewSet, basename='contacts')

urlpatterns = router.urls
