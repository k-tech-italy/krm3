from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from krm3.missions.models import Expense, ExpenseCategory, Mission, PaymentCategory

from ..session import EXPENSE_UPLOAD_IMAGES
from .serializers.expense import (ExpenseCategorySerializer, ExpenseImageUploadSerializer,
                                  ExpenseNestedSerializer, ExpenseRetrieveSerializer, PaymentCategorySerializer,)
from .serializers.mission import MissionNestedSerializer


class MissionAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MissionNestedSerializer
    queryset = Mission.objects.all()


class ExpenseAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseNestedSerializer
    queryset = Expense.objects.all()

    # TODO: Should really be an eTag?
    @action(
        detail=True,
        permission_classes=[]
    )
    def check_ts(self, request, pk):
        """Check if the record has been modified.

        Return 304 for not modified or 204 (no content) if modified"""
        ms = request.GET['ms']
        expense: Expense = self.get_object()
        return Response(status=304 if expense.get_updated_millis() == int(ms) else 204)

    @action(
        detail=True,
        serializer_class=ExpenseRetrieveSerializer
    )
    def otp(self, request, pk=None):
        return super().retrieve(request, pk=pk)

    @action(
        methods=['patch'],
        detail=True,
        permission_classes=[],
        serializer_class=ExpenseImageUploadSerializer
        # parser_classes=(MultiPartParser, FormParser)
    )
    def upload_image(self, request, *args, **kwargs):
        """Upload the image to the mission."""
        expense: Expense = self.get_object()

        serializer = self.get_serializer(expense, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if expense.check_otp(serializer.validated_data['otp']):
            self.perform_update(serializer)
            expense.image = serializer.validated_data['image']
            expense.save()

            if next := request.session.pop(EXPENSE_UPLOAD_IMAGES, []):
                next, others = next[0], next[1:] if len(next) > 1 else []
                if others:
                    request.session[EXPENSE_UPLOAD_IMAGES] = others
                url = f"{reverse('admin:missions_expense_changelist')}{next}/view_qr/"
                return HttpResponseRedirect(reverse(url))
            else:
                return Response(status=204)
        else:
            raise serializers.ValidationError('OTP not matching')

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class ExpenseCategoryAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseCategorySerializer
    queryset = ExpenseCategory.objects.all()


class PaymentCategoryAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentCategorySerializer
    queryset = PaymentCategory.objects.all()
