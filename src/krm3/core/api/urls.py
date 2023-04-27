from rest_framework.routers import SimpleRouter

from .views import BlacklistRefreshAPIViewSet, CityAPIViewSet, ProjectAPIViewSet, ResourceAPIViewSet

router = SimpleRouter()
router.register('blacklist', BlacklistRefreshAPIViewSet, basename='api-refreshtoken')
router.register('resource', ResourceAPIViewSet, basename='api-resources')
router.register('city', CityAPIViewSet, basename='api-city')
router.register('project', ProjectAPIViewSet, basename='api-project')


urlpatterns = [
]

urlpatterns += router.urls
