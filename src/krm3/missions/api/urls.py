from rest_framework.routers import SimpleRouter

from .views import ExpenseAPIViewSet, MissionAPIViewSet

router = SimpleRouter()
router.register('mission', MissionAPIViewSet, basename='api-missions-mission')
router.register('expense', ExpenseAPIViewSet, basename='api-missions-expense')

urlpatterns = router.urls
