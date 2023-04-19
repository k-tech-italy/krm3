from rest_framework.routers import SimpleRouter

from krm3.core.api.urls import urlpatterns as core_urls
from krm3.missions.api.urls import urlpatterns as missions_urls

router = SimpleRouter()
# router.register('user', UserViewSet, basename='user')

urlpatterns = router.urls + missions_urls + core_urls
