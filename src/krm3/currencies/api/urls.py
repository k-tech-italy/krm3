from rest_framework.routers import SimpleRouter

from .views import RateAPIViewSet

router = SimpleRouter()
router.register('rate', RateAPIViewSet)

urlpatterns = router.urls
