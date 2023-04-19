from rest_framework.routers import SimpleRouter

from .views import MissionAPIViewSet

router = SimpleRouter()
router.register('mission', MissionAPIViewSet, basename='api-missions-mission')

urlpatterns = router.urls
