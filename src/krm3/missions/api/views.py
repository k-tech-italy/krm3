from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from rest_framework import mixins, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from krm3.core.models import DocumentType, Expense, ExpenseCategory, Mission, PaymentCategory

from ..session import EXPENSE_UPLOAD_IMAGES
from .serializers.expense import (DocumentTypeSerializer, ExpenseCategorySerializer, ExpenseCreateSerializer,
                                  ExpenseRetrieveSerializer, ExpenseSerializer, PaymentCategorySerializer,
                                  ExpenseImageUploadSerializer )
from .serializers.mission import MissionCreateSerializer, MissionNestedSerializer
from ...utils.queryset import ACLMixin


class MissionAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MissionNestedSerializer
    queryset = Mission.objects.all()

    def get_queryset(self):
        return Mission.objects.filter_acl(self.request.user)

    def get_serializer_class(self):
        """Change serializer to MissionCreateSerializer for object creation."""
        if self.request.method in ['POST', 'PATCH']:
            return MissionCreateSerializer
        return super().get_serializer_class()


class ExpenseAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()

    def get_queryset(self):
        return Expense.objects.filter_acl(self.request.user)

    def get_serializer_class(self):
        """Change serializer to ExpenseCreateSerializer for object creation."""
        if self.request.method in ['POST', 'PATCH']:
            return ExpenseCreateSerializer
        return super().get_serializer_class()

    # TODO: Should really be an eTag?
    @action(detail=True, permission_classes=[])
    def check_ts(self, request, pk):
        """Check if the record has been modified.

        Return 304 for not modified or 204 (no content) if modified
        """
        ms = request.GET['ms']
        expense: Expense = self.get_object()
        return Response(status=304 if expense.get_updated_millis() == int(ms) else 204)

    @action(detail=True, serializer_class=ExpenseRetrieveSerializer)
    def otp(self, request, pk=None):
        return super().retrieve(request, pk=pk)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class ExpenseCategoryAPIViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseCategorySerializer
    queryset = ExpenseCategory.objects.all()


class PaymentCategoryAPIViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentCategorySerializer
    queryset = PaymentCategory.objects.all()


class DocumentTypeAPIViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentTypeSerializer
    queryset = DocumentType.objects.filter(active=True)
