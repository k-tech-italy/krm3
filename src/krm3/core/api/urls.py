from rest_framework.routers import SimpleRouter

from .views import BlacklistRefreshAPIViewSet

router = SimpleRouter()
router.register('blacklist', BlacklistRefreshAPIViewSet, basename='api-refreshtoken')

urlpatterns = [
]

urlpatterns += router.urls
