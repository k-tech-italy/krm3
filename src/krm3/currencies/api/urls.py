from rest_framework.routers import SimpleRouter

from .views import CurrencyAPIViewSet, RateAPIViewSet

router = SimpleRouter()
router.register('rate', RateAPIViewSet)
router.register('currency', CurrencyAPIViewSet)

urlpatterns = router.urls
