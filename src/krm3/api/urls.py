from django.urls import include, path
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

urlpatterns = [
    path('missions/', include(('krm3.missions.api.urls', 'missions'))),
    path('core/', include(('krm3.core.api.urls', 'core'))),
    path('currencies/', include(('krm3.currencies.api.urls', 'currencies'))),
]

urlpatterns += router.urls
