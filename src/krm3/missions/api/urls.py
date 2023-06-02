from rest_framework.routers import SimpleRouter

from .views import ExpenseAPIViewSet, MissionAPIViewSet

router = SimpleRouter()
router.register('mission', MissionAPIViewSet)
router.register('expense', ExpenseAPIViewSet)

urlpatterns = router.urls
