from rest_framework.routers import SimpleRouter

from .views import ExpenseAPIViewSet, MissionAPIViewSet, ExpenseCategoryAPIViewSet, PaymentCategoryAPIViewSet

router = SimpleRouter()
router.register('mission', MissionAPIViewSet)
router.register('expense', ExpenseAPIViewSet)
router.register('expense_category', ExpenseCategoryAPIViewSet)
router.register('payment_category', PaymentCategoryAPIViewSet)

urlpatterns = router.urls
