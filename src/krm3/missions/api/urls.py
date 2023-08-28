from rest_framework.routers import SimpleRouter

from .views import (DocumentTypeAPIViewSet, ExpenseAPIViewSet, ExpenseCategoryAPIViewSet,
                    MissionAPIViewSet, PaymentCategoryAPIViewSet,)

router = SimpleRouter()
router.register('mission', MissionAPIViewSet)
router.register('expense', ExpenseAPIViewSet)
router.register('expense_category', ExpenseCategoryAPIViewSet)
router.register('payment_category', PaymentCategoryAPIViewSet)
router.register('document_type', DocumentTypeAPIViewSet)

urlpatterns = router.urls
