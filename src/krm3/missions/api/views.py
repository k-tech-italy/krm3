from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from krm3.core.api.permissions import FeatureFlagEnabled, IsOwnerOrManager
from krm3.core.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory

from .serializers.expense import (
    DocumentTypeSerializer,
    ExpenseCategorySerializer,
    ExpenseCreateSerializer,
    ExpenseRetrieveSerializer,
    ExpenseSerializer,
    PaymentCategorySerializer,
)
from .serializers.mission import MissionCreateSerializer, MissionNestedSerializer


class MissionAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, FeatureFlagEnabled, IsOwnerOrManager]
    feature_flag = 'TRASFERTE_ENABLED'
    owner_field = 'resource.user_id'
    manage_permission = 'core.manage_any_mission'
    serializer_class = MissionNestedSerializer
    queryset = Mission.objects.all()

    def get_queryset(self) -> QuerySet[Mission]:
        return Mission.objects.filter_acl(self.request.user)

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        """Change serializer to MissionCreateSerializer for object creation."""
        if self.request.method in ['POST', 'PATCH'] and self.action != 'submit':
            return MissionCreateSerializer
        return super().get_serializer_class()

    def create(self, request: Request, *args, **kwargs) -> Response:  # noqa: ANN002, ANN003
        if not request.user.has_perm('core.add_mission'):
            raise PermissionDenied(_('You cannot create missions'))
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def submit(self, request: Request, pk: str | None = None) -> Response:
        """Transition the mission from DRAFT to SUBMITTED, assigning its number."""
        mission: Mission = self.get_object()  # owner or manager only (IsOwnerOrManager)
        try:
            mission.submit()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return Response(self.get_serializer(mission).data)


class ExpenseAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, FeatureFlagEnabled, IsOwnerOrManager]
    feature_flag = 'TRASFERTE_ENABLED'
    owner_field = 'mission.resource.user_id'
    manage_permission = 'core.manage_any_expense'
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()

    def get_queryset(self) -> QuerySet[Expense]:
        return Expense.objects.filter_acl(self.request.user)

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        """Change serializer to ExpenseCreateSerializer for object creation."""
        if self.request.method in ['POST', 'PATCH']:
            return ExpenseCreateSerializer
        return super().get_serializer_class()

    # TODO: Should really be an eTag?
    @action(detail=True, permission_classes=[FeatureFlagEnabled])
    def check_ts(self, request: Request, pk: str) -> Response:
        """Check if the record has been modified.

        Return 304 for not modified or 204 (no content) if modified
        """
        ms = request.GET['ms']
        expense: Expense = self.get_object()
        return Response(status=304 if expense.get_updated_millis() == int(ms) else 204)

    @action(detail=True, serializer_class=ExpenseRetrieveSerializer)
    def otp(self, request: Request, pk: str | None = None) -> Response:
        return super().retrieve(request, pk=pk)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        return super().partial_update(request, *args, **kwargs)


class ExpenseCategoryAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, FeatureFlagEnabled]
    feature_flag = 'TRASFERTE_ENABLED'
    serializer_class = ExpenseCategorySerializer
    queryset = ExpenseCategory.objects.all()


class PaymentCategoryAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, FeatureFlagEnabled]
    feature_flag = 'TRASFERTE_ENABLED'
    serializer_class = PaymentCategorySerializer
    queryset = PaymentCategory.objects.all()


class DocumentTypeAPIViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, FeatureFlagEnabled]
    feature_flag = 'TRASFERTE_ENABLED'
    serializer_class = DocumentTypeSerializer
    queryset = DocumentType.objects.filter(active=True)
