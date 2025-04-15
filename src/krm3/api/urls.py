from django.urls import include, path
from rest_framework.routers import SimpleRouter

router = SimpleRouter()

urlpatterns = [
    path('missions/', include(('krm3.missions.api.urls', 'missions-api'))),
    path('core/', include(('krm3.core.api.urls', 'core-api'))),
    path('currencies/', include(('krm3.currencies.api.urls', 'currencies-api'))),
    path('timesheet/', include(('krm3.timesheet.api.urls', 'timesheet-api'))),
]

urlpatterns += router.urls
