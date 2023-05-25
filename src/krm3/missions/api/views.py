from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from krm3.missions.models import Expense, Mission

from .serializers.expense import ExpenseSerializer, ExpenseImageUploadSerializer
from .serializers.mission import MissionSerializer


class MissionAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MissionSerializer
    queryset = Mission.objects.all()


class ExpenseAPIViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExpenseSerializer
    queryset = Expense.objects.all()

    @action(
        methods=['post'],
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
        else:
            raise APIException(code=400, detail='Invalid OTP')

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


